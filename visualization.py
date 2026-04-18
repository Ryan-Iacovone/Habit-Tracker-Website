import matplotlib.pyplot as plt
import matplotlib
import plotly.express as px
import plotly.io as pio
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
from plotnine import *
from data_cleaning import Read_Apple_Workouts, gen_month_freq_df, gen_distance_df, gen_mins_df, gen_workout_time_df, gen_activity_treemap_df, gen_steps_month_df, gen_weekly_workout_time_df

matplotlib.use('Agg')  # use non-GUI backend for Flask app

# Grab today's date once, then have it pass through each funtion
today = datetime.now(tz=ZoneInfo("US/Eastern"))

# List of date filter calculations we can pass through
l_3_m = today - relativedelta(weeks=14)
l_7_m = today - relativedelta(months=7)
l_1_y = today - relativedelta(years=1)


# Apple workout data from data_cleaning file
aw_all = Read_Apple_Workouts()


############### Frequency bar chart grouped by exercise type and month ###############
def Monthly_Freq_BarChart():
    month_count_data = gen_month_freq_df(aw_all, l_7_m)
    plot = (ggplot(month_count_data, aes(x='month', y='n', fill='activity')) + 
        geom_bar(stat='identity', position='dodge', color = "Black") +
        
        geom_text(aes(label='n'), position=position_dodge(width=0.9), va='bottom') + # va & ha are used for veritcal and horizontal allignment 
        
        scale_fill_brewer(type='qual', palette='Set2') +
        scale_y_continuous(breaks = range(0, 14, 2),
                        limits = [0, 13]) +

        labs(title='Workout Frequency by Month and Activity',
            x='',
            y='Sessions',
            fill='Activity',
            color='Goal') +
        #theme_matplotlib() +
        theme_seaborn() +
        theme(figure_size=(10, 5)))

    fig = plot.draw() # Render plot to a matplotlib figure
    buf = io.BytesIO() # Save figure to buffer (RAM)
    fig.savefig(buf, format='png', bbox_inches='tight') # Instead of writing chart.png to your hard drive, matplotlib writes the PNG bytes into that in-memory "file"
    plt.close(fig) # Close the figure to free up memory
    buf.seek(0) # Reinitializing the buffer position

    return buf 



############### Frequency bar chart grouped by exercise type and week ###############
""" week_count_data = gen_week_freq_df(aw_all, l_3_m)

def Weekly_Freq_BarChart():

    plot = (ggplot(week_count_data, aes(x='week', y='n', fill='activity')) +
        geom_bar(stat='identity', position='dodge', color = "Black") +
        geom_text(aes(label='n'), position=position_dodge(width=0.9), va='bottom') + # va & ha are used for veritcal and horizontal allignment 
        
        scale_fill_brewer(type='qual', palette='Set2') +
        #scale_color_manual(values={'Running': 'Black', 'Cycling': 'Gray'}) +
        scale_y_continuous(breaks = range(0, 6),
                        limits = [0, 5]) +

        labs(title='Workout Frequency by Week and Activity',
            x='',
            y='Sessions',
            fill='Activity') +
        #theme_matplotlib() +
        theme_seaborn() +
        theme(figure_size=(10, 5)))

    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    frequency_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return frequency_plot_url  """


############### Distance per week grouped by exercise type ###############


def Distance_BarChart():
    full_miles_week, y_limit = gen_distance_df(aw_all, l_3_m)

    plot = (ggplot(full_miles_week, aes(x='week', y='Total_Miles', group='activity')) +

    geom_line(aes(color='activity'), size=2) +
    geom_point(aes(color='activity'), size=1.5) +

    # geom_bar(stat='identity', position='dodge', color = "Black") +

    geom_text(aes(label='Total_Miles'), va='bottom', nudge_y = .35) +  # position=position_dodge(width=.9),

    scale_y_continuous(breaks=range(0, y_limit, 5),
                       # minor_breaks=range(0, 36, 2),  # Can't do minor ticks 2.5 because int not float :(
                       limits=[0, y_limit]) +

    scale_color_manual(values={'Running': '#a259d9',
                               'Cycling': '#ff9800'}) +

    labs(title="Cardio Miles per Week",
         x="",
         y="Miles",
         fill="Activity") +
    #theme_seaborn() +

    theme(figure_size=(10, 5),
          legend_position=(.5, .95),
          legend_title=element_blank(),
          legend_direction='horizontal',
          legend_text=element_text(color="Black", size=9),
          legend_background=element_blank(),  # element_rect(fill="#1E2A38", color=None),
          legend_key=element_blank(),  # Removes boxing/shading around lines in legend

          panel_grid_minor_y=element_line(color="White", linetype="solid")))

    fig = plot.draw() # Render plot to a matplotlib figure
    buf = io.BytesIO() # Save figure to buffer (RAM)
    fig.savefig(buf, format='png', bbox_inches='tight') # Instead of writing chart.png to your hard drive, matplotlib writes the PNG bytes into that in-memory "file"
    plt.close(fig) # Close the figure to free up memory
    buf.seek(0) # Reinitializing the buffer position

    return buf


############### Minutes per week grouped by cardio and weights ###############
def Minutes_BarChart():
    full_mins_cardio, cardio_labels, full_mins_weight, y_max = gen_mins_df(aw_all, l_3_m)

    plot = (ggplot() +

        # Cardio stacked bar chart by activity subtypes (nudged to the left)
        geom_bar(
            data=full_mins_cardio,
            mapping=aes(x='x_nudged', y='Total_min', fill='activity'),
            stat='identity', position='stack', width=2, color='#b36a62', size=0.7 ) +

        # Cardio Labels: minutes for each cardio subtype
        geom_text(
            data=cardio_labels,
            mapping=aes(x='x_nudged', y='cumsum_min', label='Total_min'),
            #format_string='{:.1f}', 
            va='bottom', color='black', size=10 ) +

        # Weights barchart, not stacked because only 1 activity type (nudged right)
        geom_bar(
            data=full_mins_weight,
            mapping=aes(x='x_nudged', y='Total_min', fill='activity'),
            stat='identity', position='stack', width=2, color='#549f74', size=0.7 ) +

        # Weight labels: count of weight exercises per week
        geom_text(data = full_mins_weight,
                mapping= aes(x='x_nudged', y='Total_min', label='n'), 
                va='bottom', color = "black", size = 10) +

        # 
        scale_fill_manual(values= {"Swimming": "#00C9D4",
                                "Cycling":  "#FF6B2B",
                                "Running":  "#E63946",
                                "Walking":  "#9B8EC4",
                                "TraditionalStrengthTraining":  "#7EBC1A"},
                                labels={"TraditionalStrengthTraining": "Weights"}) +

        # Setting goal lines for cardio and weight exercises per week
        geom_hline(yintercept=150, color="#b36a62", linetype='dashed', size=1) +
        geom_hline(yintercept=80,  color="#549f74", linetype='dashed', size=1) + 

        scale_y_continuous(breaks=range(0, y_max, 50), 
                        limits=[0, y_max]) +

        scale_x_datetime(date_breaks='1 week', 
                        date_labels='%b %d',
                     expand=(.01, 0))  +

        labs(title="Minutes per Week by Activity", 
            x="", 
            y="Minutes", 
            fill="") +

        theme(
            figure_size=(10, 5),
            legend_position= (.5, .95),
            legend_title=element_text(color="#E8EFF5", size=11, weight='bold'),
            legend_direction='horizontal',
            legend_text=element_text(color="#A0B4C8", size=9),
            legend_background= element_blank(), #element_rect(fill="#1E2A38", color=None),
            legend_key=element_blank(), # Removes boxing/shading around lines in legend
            #plot_background   = element_rect(fill="#141C26", color=None),
            #panel_background  = element_rect(fill="#1E2A38", color=None),
            #panel_grid_major  = element_line(color="#2E3D4F", size=0.5),
            #panel_grid_minor  = element_line(color="#243040", size=0.3),
            axis_text = element_text(color="#6B8299", size=9),
            axis_title = element_text(color="#A0B4C8", size=10),
            plot_title = element_text(color="#E8EFF5", size=13, weight="bold"))
    )
    
    fig = plot.draw() # Render plot to a matplotlib figure
    buf = io.BytesIO() # Save figure to buffer (RAM)
    fig.savefig(buf, format='png', bbox_inches='tight') # Instead of writing chart.png to your hard drive, matplotlib writes the PNG bytes into that in-memory "file"
    plt.close(fig) # Close the figure to free up memory
    buf.seek(0) # Reinitializing the buffer position

    return buf


######## Workout time by week over time ########
def weekly_workout_time_linegraph():
    workout_time_df = gen_weekly_workout_time_df(aw_all)

    plot = (ggplot(workout_time_df, aes(x='plot_date', y='Hours', group='Year', color='Year')) +
            geom_line(size=1.2) +
            geom_point(color="Black", size=.8) +
            # geom_text(aes(label='Hours'), position=position_dodge(width=0.9), va='bottom') + # va & ha are used for veritcal and horizontal allignment

            geom_hline(yintercept=3, color="#549f74", linetype='dashed', size=1) +  # Cardio goal

            # scale_fill_brewer(type='qual', palette='Set2') +
            scale_color_manual(values={'2024': "#52be80", '2025': '#ec7063', '2026': "#3414B3"}) +

            scale_x_datetime(date_labels='%b', date_breaks='1 month',
                             expand=(0, 8, 0, 1)) +  # https://plotnine.org/reference/scale.html

            scale_y_continuous(breaks=range(0, 11),
                               # Defining breaks of y axis (every number between 0 and 10 within the limit)
                               limits=[0, 10]) +  # Defining zoom of y axis

            labs(title='Workout Duration by Week and Activity',
                 x='',
                 y='Hours',
                 color='Year') +
            # theme_matplotlib() +
            # theme_seaborn() +
            theme(figure_size=(10, 5),
                  axis_ticks_length_minor_y=0,  # Turn off minor ticks by setting length to be 0
                  axis_text_x=element_text(vjust=1),

                  plot_background=element_rect(fill='#1a1a1a'),
                  panel_background=element_rect(fill='#2d2d2d'),
                  legend_position='top',
                  legend_title=element_text(color='white', size=11, weight='bold'),
                  legend_direction='horizontal',
                  legend_text=element_text(color='white', size=9),
                  legend_background=element_blank(),
                  legend_key=element_blank(),  # Removes boxing/shading around lines in legend
                  axis_text=element_text(color='white', size=9),
                  axis_title=element_text(color='white', size=10),  # Axis labels
                  plot_title=element_text(color='white', size=14, weight='bold'),  # plot title
                  panel_grid_major=element_line(color='#404040', size=1)
                  )
            )

    fig = plot.draw() # Render plot to a matplotlib figure
    buf = io.BytesIO() # Save figure to buffer (RAM)
    fig.savefig(buf, format='png', bbox_inches='tight') # Instead of writing chart.png to your hard drive, matplotlib writes the PNG bytes into that in-memory "file"
    plt.close(fig) # Close the figure to free up memory
    buf.seek(0) # Reinitializing the buffer position

    return buf


############### Minutes per week for all exercises ############### 
"""workout_time = gen_workout_time_df(aw_all, l_3_m)
 
def Minutes_LineGraph():
    plot = (ggplot(workout_time, aes(x='week', y='Time')) +
        geom_line(color = "blue", size = 1) +
        #geom_point(aes(size = "n"), alpha = 0.6, color = "blue") +
        #geom_text(aes(label='n'), format_string='{:.0f}', va='bottom') +
        
        labs(title= "Minutes per Week by Activity",
            x="Week",
            y="Minutes") +

        #scale_x_datetime(date_labels='%b %d', date_breaks='1 week') +
        
        theme_seaborn() +
        
        theme(panel_grid_minor_y = element_line(color = "gray", linetype = "dotted"),
            figure_size=(10, 5),
            axis_text_x=element_text(angle=25, hjust=1),
            legend_position='none',
            axis_ticks_minor_x=element_blank()))

    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    total_mins_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return total_mins_plot_url"""


############### Step count grouped by month ############### 
def Steps_Boxplot():
    apple_steps = gen_steps_month_df(l_1_y)
    plot = (
        ggplot(apple_steps, aes(x='month', y='value', fill='month')) +

        geom_boxplot(color="black") +
        stat_summary(fun_data="mean_cl_boot", geom = "point", fill = "white", color = "red") +

        labs(title="Daily Steps Grouped by Month", 
            x="", 
            y="Steps") +

        scale_y_continuous(breaks = range(0, 32500, 5000),
                        minor_breaks=range(0, 32500, 2500),  # Can't do minor ticks 2.5 because int not float :(
                        limits = [0, 30000]) +

        theme_seaborn() +

        theme(axis_text_x=element_text(),
            figure_size=(10, 5),
            legend_position='none',
            panel_grid_minor_y = element_line(color = "White", linetype = "dotted")))

    fig = plot.draw() # Render plot to a matplotlib figure
    buf = io.BytesIO() # Save figure to buffer (RAM)
    fig.savefig(buf, format='png', bbox_inches='tight') # Instead of writing chart.png to your hard drive, matplotlib writes the PNG bytes into that in-memory "file"
    plt.close(fig) # Close the figure to free up memory
    buf.seek(0) # Reinitializing the buffer position

    return buf



############### Activity Treemap ############### 
def activity_treemap():
    activity_distribution = gen_activity_treemap_df(aw_all, l_3_m)

    # Create treemap
    fig = px.treemap(
        activity_distribution,
        path=['label'],         # use custom label for full text
        values='n',
        color='n',
        color_continuous_scale='Blues')

    fig.update_traces(hovertemplate='%{label}')  
    fig.update_layout(showlegend=False, coloraxis_showscale=False)

    treemap_plotly_html = pio.to_html(fig, full_html=False)

    return treemap_plotly_html