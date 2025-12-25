import matplotlib.pyplot as plt
import matplotlib
import plotly.express as px
import plotly.io as pio
import io
import base64
import pandas as pd 
from plotnine import *
from Data_Cleaning import Read_Apple_Workouts, gen_month_freq_df, gen_week_freq_df, gen_distance_df, gen_mins_df, gen_workout_time_df, gen_activity_treemap_df, gen_steps_month_df

matplotlib.use('Agg')  # use non-GUI backend for Flask app


# Grab today's date once, then have it pass through each funtion
today = pd.Timestamp.now(tz="America/New_York")

# List of date filter calculations we can pass through
l_3_m = (today - pd.DateOffset(weeks=14)).normalize() # Normalize sets the time to midnight
l_7_m = (today - pd.DateOffset(months=7)).to_period('M') # 
l_1_y = (today - pd.DateOffset(months=12)).to_period('M') # 


# Apple workout data from data_cleaning file
aw_final = Read_Apple_Workouts()


############### Frequency bar chart grouped by exercise type and month ###############
month_count_data = gen_month_freq_df(aw_final, l_7_m)

def Monthly_Freq_BarChart():
        
    plot = (ggplot(month_count_data, aes(x='month_label', y='n', fill='activity')) + 
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

    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    frequency_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return frequency_plot_url 



############### Frequency bar chart grouped by exercise type and week ###############
week_count_data = gen_week_freq_df(aw_final, l_3_m)

def Weekly_Freq_BarChart():

    plot = (ggplot(week_count_data, aes(x='week_label', y='n', fill='activity')) +
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

    return frequency_plot_url 


############### Distance per week grouped by exercise type ###############
full_miles_week = gen_distance_df(aw_final, l_3_m)

def Distance_BarChart():
        
    plot = (ggplot(full_miles_week, aes(x='week_label', y='Total_Miles', fill='activity')) +
        geom_bar(stat='identity', position='dodge', color = "Black") +
        geom_text(aes(label='Total_Miles'), position=position_dodge(width=.9), va='bottom') +

        scale_y_continuous(breaks = range(0, 36, 5),
                        #minor_breaks=range(0, 36, 2),  # Can't do minor ticks 2.5 because int not float :(
                        limits = [0, 36]) +

        scale_fill_manual(values={'Running': '#a259d9',   
            'Cycling': '#ff9800'}) +

        labs(title= "Cardio Miles per Week",
            x="",
            y="Miles",
            fill = "Activity") +
        theme_seaborn() +
        theme(figure_size=(10, 5),
            panel_grid_minor_y = element_line(color = "White", linetype = "dotted")))

    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    distance_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return distance_plot_url


############### Minutes per week grouped by cardio and weights ###############
full_mins_week = gen_mins_df(aw_final, l_3_m)

def Minutes_BarChart():
    plot = (ggplot(full_mins_week, aes(x='week_label', y='Total_min', fill='activity_type')) +
        geom_bar(stat='identity', position='dodge', color = "Black") +
        geom_text(aes(label='Total_min'), format_string='{:.1f}',position=position_dodge(width=.9), va='bottom') + #Format count?

        geom_hline(yintercept=150, color="#549f74", linetype='dashed', size=1) + # Cardio goal
        geom_hline(yintercept=80, color="#b36a62", linetype='dashed', size=1) + # Weights goal
        
        scale_y_continuous(breaks = range(0, 450, 50),
                        #minor_breaks=range(0, 36, 2),  # Can't do minor ticks 2.5 because int not float :(
                        limits = [0, 400]) +

        # Manual color scales
        scale_fill_manual(values={'Cardio': '#52be80', 'Weights': '#ec7063'}) +  # Bar colors
        
        labs(title= "Minutes per Week by Activity",
            x="",
            y="Minutes", 
            fill="Activity") +
        
        theme_seaborn() +
        theme(figure_size=(10, 5),
            panel_grid_minor_y = element_line(color = "White", linetype = "dotted")))
    
    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    mins_plot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return mins_plot_url

############### Minutes per week for all exercises ############### 
workout_time = gen_workout_time_df(aw_final, l_7_m)
 
def Minutes_LineGraph():
    plot = (ggplot(workout_time, aes(x='week_period', y='Time')) +
        geom_line(color = "blue", size = 1) +
        geom_point(aes(size = "n"), alpha = 0.6, color = "blue") +
        geom_text(aes(label='n'), format_string='{:.0f}', va='bottom') +
        labs(title= "Minutes per Week by Activity",
            x="Week",
            y="Minutes") +
        scale_x_datetime(date_labels='%b %d', date_breaks='1 week') +
        
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

    return total_mins_plot_url


############### Step count grouped by month ############### 
steps_day = gen_steps_month_df(l_1_y)

def Steps_Boxplot():
    plot = (
        ggplot(steps_day, aes(x='month_label', y='steps', fill='month_label')) +

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

    # Render plot to a matplotlib figure
    fig = plot.draw()

    # Save figure to buffer
    static_bytes = io.BytesIO()
    fig.savefig(static_bytes, format='png', bbox_inches='tight')
    static_bytes.seek(0)
    static_base64 = base64.b64encode(static_bytes.read()).decode('utf-8')
    steps_boxplot_url = f"data:image/png;base64,{static_base64}"
    plt.close(fig)

    return steps_boxplot_url



############### Activity Treemap ############### 
activity_distribution = gen_activity_treemap_df(aw_final, l_3_m)

def activity_treemap():
    # Create treemap
    fig = px.treemap(
        activity_distribution,
        path=['label'],         # use custom label for full text
        values='count',
        color='count',
        color_continuous_scale='Blues')
    
    fig.update_traces(hovertemplate='%{label}')  
    fig.update_layout(showlegend=False, coloraxis_showscale=False)

    treemap_plotly_html = pio.to_html(fig, full_html=False)

    return treemap_plotly_html