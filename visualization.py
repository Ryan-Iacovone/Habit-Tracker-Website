import matplotlib.pyplot as plt
import matplotlib
import plotly.express as px
import plotly.io as pio
import io
import pandas as pd
from sqlalchemy import text
from zoneinfo import ZoneInfo
from datetime import datetime
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
from plotnine import *
from data_cleaning import Read_Apple_Workouts, gen_month_freq_df, gen_distance_df, gen_mins_df, gen_workout_time_df, gen_activity_treemap_df, gen_steps_month_df, gen_weekly_workout_time_df
from db import engine

matplotlib.use('Agg')  # use non-GUI backend for Flask app

# Grab today's date once, then have it pass through each funtion
today = datetime.now(tz=ZoneInfo("US/Eastern"))

# List of date filter calculations we can pass through
l_3_m = today - relativedelta(weeks=14)
l_7_m = today - relativedelta(months=7)
l_1_y = today - relativedelta(years=1)


# Apple workout data from data_cleaning file
aw_all = Read_Apple_Workouts()

# Statically defining custom workout theme for all graphs
workout_theme = theme(
    figure_size=(10, 5),
    legend_position=(.5, .96),
    #legend_title=element_text(color="#1E3A52", size=11, weight='bold'),
    legend_direction='horizontal',
    legend_text=element_text(color="#3A5A78", size=11),
    legend_background=element_blank(),
    legend_key=element_blank(),

    plot_background  = element_rect(fill="#FFFFFF", color=None),
    panel_background = element_rect(fill="#F4F7FA", color=None),
    panel_grid_major = element_line(color="#CDDDED", size=0.5),
    panel_grid_minor_y = element_line(color="#CDDDED", linetype="solid"),

    axis_text        = element_text(color="#6B8299", size=10), # X & Y axis labels
    axis_title       = element_text(color="#3A5A78", size=13), # y axis title/label
    #plot_title       = element_text(color="#1E3A52", size=13, weight="bold"),
)


############### Frequency bar chart grouped by exercise type and month ###############
def Monthly_Freq_BarChart():
    month_count_data, session_y_max = gen_month_freq_df(aw_all, l_7_m)
    plot = (ggplot(month_count_data, aes(x='month', y='n', fill='activity')) + 
    geom_bar(stat='identity', position='dodge', color = "Black") +
    
    geom_text(aes(label='n'), position=position_dodge(width=0.9), va='bottom') + # va & ha are used for veritcal and horizontal allignment 
    
    scale_fill_manual(values= {"Swimming": "#3A8FD4",
                                "Cycling":  "#FF6B2B",
                                "Running":  "#7B5EA7", 
                                "Walking":  "#E63946",
                                "Weights":  "#2EAF6E"} ) +


    scale_y_continuous(breaks = range(0, session_y_max + 1, 2),
                    limits = [0, session_y_max]) +

    labs(title='',
        x='',
        y='Sessions',
        fill='') +

    workout_theme 
        )


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

    plot = (ggplot(full_miles_week, aes(x='week', y='Total_Miles', group='activity', color='activity')) +

    geom_line(size=2) +
    geom_point(size=2) +

    # geom_bar(stat='identity', position='dodge', color = "Black") +

    geom_text(aes(label='Total_Miles'), color = "black", va='bottom', nudge_y = .35) +  # position=position_dodge(width=.9),

    scale_y_continuous(breaks=range(0, y_limit, 5),
                       # minor_breaks=range(0, 36, 2),  # Can't do minor ticks 2.5 because int not float :(
                       limits=[0, y_limit]) +

    scale_color_manual(values={'Running': '#7B5EA7',
                               'Cycling': '#FF6B2B'}) +

    labs(title="",
         x="",
         y="Miles",
         color="") +

    workout_theme
        )

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
            stat='identity', position='stack', width=2, color="#45484B", size=0.7 ) +

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
            stat='identity', position='stack', width=2, color='#45484B', size=0.7 ) +

        # Weight labels: count of weight exercises per week
        geom_text(data = full_mins_weight,
                mapping= aes(x='x_nudged', y='Total_min', label='n'), 
                va='bottom', color = "black", size = 10) +

        # 
        scale_fill_manual(values= {"Swimming": "#3A8FD4",
                                "Cycling":  "#FF6B2B",
                                "Running":  "#7B5EA7", 
                                "Walking":  "#E63946",
                                "TraditionalStrengthTraining":  "#2EAF6E"},
                                labels={"TraditionalStrengthTraining": "Weights"}) +

        # Setting goal lines for cardio and weight exercises per week
        geom_hline(yintercept=150, color="#b36a62", linetype='dashed', size=1) +
        geom_hline(yintercept=80,  color="#549f74", linetype='dashed', size=1) + 

        scale_y_continuous(breaks=range(0, y_max, 50), 
                        limits=[0, y_max]) +

        scale_x_datetime(date_breaks='1 week', 
                        date_labels='%b %d',
                     expand=(.01, 0))  +

        labs(title="", 
            x="", 
            y="Minutes", 
            fill="") +

        workout_theme
            )
    
    fig = plot.draw() # Render plot to a matplotlib figure
    buf = io.BytesIO() # Save figure to buffer (RAM)
    fig.savefig(buf, format='png', bbox_inches='tight') # Instead of writing chart.png to your hard drive, matplotlib writes the PNG bytes into that in-memory "file"
    plt.close(fig) # Close the figure to free up memory
    buf.seek(0) # Reinitializing the buffer position

    return buf


######## Workout time by week over time ########
def weekly_workout_time_linegraph():
    workout_time_df, y_limit = gen_weekly_workout_time_df(aw_all)

    plot = (ggplot(workout_time_df, aes(x='plot_date', y='Hours', group='Year', color='Year')) +
            geom_line(size=1.4) +
            geom_point(color="Black", size=.8) +
            # geom_text(aes(label='Hours'), position=position_dodge(width=0.9), va='bottom') + # va & ha are used for veritcal and horizontal allignment

            geom_hline(yintercept=3, color="#549f74", linetype='dashed', size=1) +  # Cardio goal
            
            scale_color_manual(values={"2024": "#B8D2ED", "2025": "#4A90C4", "2026": "#0A2E4D"} ) +

                                    # '2024': "#52be80", '2025': '#ec7063', '2026': "#3414B3"}) +

            scale_x_datetime(date_labels='%b', date_breaks='1 month',
                             expand=(0, 8, 0, 1)) +  # https://plotnine.org/reference/scale.html

            scale_y_continuous(breaks=range(0, y_limit + 1),
                               # Defining breaks of y axis (every number between 0 and 10 within the limit)
                               limits=[0, y_limit]) +  # Defining zoom of y axis

            labs(title='',
                 x='',
                 y='Hours',
                 color='') +

            workout_theme
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
    apple_steps, step_y_max = gen_steps_month_df(l_1_y)
    plot = (
        ggplot(apple_steps, aes(x='month', y='value', fill='month')) +

        geom_boxplot(color="black") +
        stat_summary(fun_data="mean_cl_boot", geom = "point", fill = "white", color = "red") +

        geom_hline(yintercept=7500, color="#549f74", linetype='dashed', size=1) + # Step goal

        labs(title="", 
            x="", 
            y="Steps") +

        scale_y_continuous(breaks = range(0, step_y_max , 5000),
                        minor_breaks=range(0, step_y_max , 2500),  # Can't do minor ticks 2.5 because int not float :(
                        limits = [0, step_y_max]) +

        workout_theme +

        # Overriding legend element to exclude legend  
        theme(legend_position='none') 
            )


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


############### KPI Stats Generation ###############

def get_kpi_stats():

    # Calculating steps per day in SQLite, then using localtime function to get to EST from UTC
    with engine.connect() as connection:
        daw = pd.read_sql_query( # daw = distinct apple workouts
            text("""SELECT DATE(aw.startDate, 'localtime') as Date, aw.activity, aw.value 
                    FROM apple_workouts aw 
                    WHERE aw.metric = 'Duration' AND aw.value > 10
                    ORDER BY aw.StartDate desc """), connection,
            #dtype={"value": "int64"},
            #params={"t_filter": l_1_y.astimezone(ZoneInfo("UTC"))},
            parse_dates=['Date'])
        
    # Creating a week categorical variable (copied from inital aw_all completion)
    # calculating out necessary time metrics when reading in apple workouts data
    ## calculates how many days each weekday is from monday and subtracts that from the orignal date to get back to start of the week Monday
    daw['week_date'] = (daw['Date'] - pd.to_timedelta(daw['Date'].dt.weekday, unit="D") ).dt.normalize() # Resulting date is in EST (I believe this is the correct move when filtering later on) # dt.weekday uses Monday as 0 

        # Create a string label for display
    daw['week'] = daw['week_date'].dt.strftime('%b %d')

    # Set 'week_label' as a categorical(factor variable) with order based on 'week_period'
    week_order = daw.sort_values('week_date')['week'].unique()
    daw['week'] = pd.Categorical(daw['week'], categories=week_order, ordered=True)


    # Gathering times for filtering
    today = datetime.now(tz=ZoneInfo("US/Eastern"))
    this_month = today.strftime('%b %Y')
    last_month = (today - relativedelta(months=1)).strftime('%b %Y')
    current_year = int(today.strftime('%Y'))
    duration_length = 10

    # Gather names for displaying on front end
    current_month_name = today.strftime('%B')
    last_month_name = (today - relativedelta(months=1)).strftime('%B') 

    # Gathering wokrout counts (classifying a true workout to be greater than 10 minutes long)
    ## Current Month Workout Count
    wokrout_count_CM = len( daw[ (daw['Date'].dt.strftime('%b %Y') == this_month) ] )
    ## Last month Workout Count
    workout_count_LM = len( daw[ (daw['Date'].dt.strftime('%b %Y') == last_month) ] )
    ## Current Year Workout Count
    workout_count_year = len( daw[ (daw['Date'].dt.year == current_year) ] )

    # Gather average weekly time spent working out using last 3 months data
    workout_time_df = daw[ (daw['Date'].dt.date > l_3_m.date() ) ].groupby(['week_date'])['value'].agg(Time='sum', n='count').reset_index()
    workout_time_hrs_avg = (workout_time_df["Time"].mean()/60).round(2) # Converting minutes to hours


    # Calculating steps per day in SQLite, then using localtime function to get to EST from UTC
    with engine.connect() as connection:
        das_l3m = pd.read_sql_query( # das_l3m = daily average steps last 3 months
            text("""SELECT AVG(value) as 'value'
                    FROM (SELECT DATE(adr.startDate, 'localtime') as Date, SUM(adr.value) as 'value' 
                            FROM apple_data_raw adr
                            WHERE type = 'StepCount' AND value IS NOT NULL AND date(startDate, 'localtime') >= :t_filter
                            GROUP BY date(startDate, 'localtime')
                            ) """), connection,
            #dtype={"value": "int64"},
            params={"t_filter": l_3_m} )   #.astimezone(ZoneInfo("UTC"))},
            #parse_dates=['Date'])

    steps_L3_mon = round(das_l3m["value"].iloc[0], 0).astype("int")


    # Saving output to csv instead of directly connecting to flask
    asaved_df = pd.DataFrame({
        'workout_count_year': workout_count_year,
        'workout_count_LM': workout_count_LM,
        'workout_count_CM': wokrout_count_CM,
        'current_month_name': current_month_name,
        'last_month_name': last_month_name,
        'workout_time_hrs_avg': workout_time_hrs_avg,
        'steps_L3_mon': steps_L3_mon
    }, index=[0])

    asaved_df.to_csv('static/kpi_stats.csv', index=False)