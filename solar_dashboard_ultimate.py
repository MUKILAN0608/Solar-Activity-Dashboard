
import dash
from dash import dcc, html, Input, Output, callback
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import dash_bootstrap_components as dbc

# Fix for orjson import issues - disable orjson to prevent serialization errors
import os
os.environ['DASH_SERIALIZER'] = 'json'

# Helper function for applying filters
def apply_filters(df, start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    """Apply all filters to the dataframe"""
    filtered_df = df.copy()
    
    # Date filter
    if start_date:
        filtered_df = filtered_df[filtered_df['observation_date'] >= start_date]
    if end_date:
        filtered_df = filtered_df[filtered_df['observation_date'] <= end_date]
    
    # Flare class filter - convert to individual flare type filters
    if flare_classes:
        # Create a mask for any flare type that matches the selected classes
        mask = pd.Series(False, index=filtered_df.index)
        if 'X' in flare_classes:
            mask |= (filtered_df['x_class_flares'] > 0)
        if 'M' in flare_classes:
            mask |= (filtered_df['m_class_flares'] > 0)
        if 'C' in flare_classes:
            mask |= (filtered_df['c_class_flares'] > 0)
        filtered_df = filtered_df[mask]
    
    # Cycle phase filter - skip if column doesn't exist
    if cycle_phases and 'cycle_phase' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['cycle_phase'].isin(cycle_phases)]
    elif cycle_phases and 'solar_cycle_phase' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['solar_cycle_phase'].isin(cycle_phases)]
    
    # Magnetic complexity filter - skip if column doesn't exist
    if magnetic_types and 'magnetic_complexity' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['magnetic_complexity'].isin(magnetic_types)]
    
    # Sunspot count filter - handle different column names
    if sunspot_range:
        if 'total_sunspots' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['total_sunspots'] >= sunspot_range[0]) & 
                (filtered_df['total_sunspots'] <= sunspot_range[1])
            ]
        elif 'sunspot_count' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['sunspot_count'] >= sunspot_range[0]) & 
                (filtered_df['sunspot_count'] <= sunspot_range[1])
            ]
    
    # Flare occurred filter - calculate total_flares if needed
    if flare_occurred:
        # Calculate total_flares if it doesn't exist
        if 'total_flares' not in filtered_df.columns:
            filtered_df['total_flares'] = filtered_df['x_class_flares'] + filtered_df['m_class_flares'] + filtered_df['c_class_flares']
        
        if 'Yes' in flare_occurred and 'No' not in flare_occurred:
            filtered_df = filtered_df[filtered_df['total_flares'] > 0]
        elif 'No' in flare_occurred and 'Yes' not in flare_occurred:
            filtered_df = filtered_df[filtered_df['total_flares'] == 0]
    
    return filtered_df

# Load the datasets with error handling
print("Loading data...")
import time
import os

# Ensure files are not locked
def safe_read_csv(filename, max_retries=3):
    for attempt in range(max_retries):
        try:
            df = pd.read_csv(filename)
            return df
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {filename}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait 2 seconds before retry
            else:
                raise e

try:
    solar_flare_df = safe_read_csv('solar_flare_data_cleaned.csv')
    print(f"Solar flare data loaded: {len(solar_flare_df)} records")
except Exception as e:
    print(f"Failed to load solar flare data after retries: {e}")
    raise

try:
    sunspot_df = safe_read_csv('sunspot_activity_cleaned.csv')
    print(f"Sunspot data loaded: {len(sunspot_df)} records")
except Exception as e:
    print(f"Failed to load sunspot data after retries: {e}")
    raise

# Convert date columns
solar_flare_df['observation_date'] = pd.to_datetime(solar_flare_df['observation_date'])
sunspot_df['date'] = pd.to_datetime(sunspot_df[['year', 'month']].assign(day=1))

# Sunspot data already has total_sunspots column, no mapping needed

# Optimize data types to reduce memory usage
solar_flare_df = solar_flare_df.astype({
    'x_class_flares': 'int16',
    'm_class_flares': 'int16', 
    'c_class_flares': 'int16',
    'sunspot_count': 'int16',
    'flare_occurred': 'int8'
})

print(f"Data loaded successfully: {len(solar_flare_df)} flare records, {len(sunspot_df)} sunspot records")

# Filter data only until 2024
solar_flare_df = solar_flare_df[solar_flare_df['observation_date'].dt.year <= 2024].copy()
sunspot_df = sunspot_df[sunspot_df['date'].dt.year <= 2024].copy()

# Calculate month range for slider
min_date = solar_flare_df['observation_date'].min()
max_date = solar_flare_df['observation_date'].max()
min_date_for_slider = pd.to_datetime(min_date.strftime('%Y-%m-01'))
max_date_for_slider = pd.to_datetime(max_date.strftime('%Y-%m-01'))
total_months = (max_date_for_slider.year - min_date_for_slider.year) * 12 + max_date_for_slider.month - min_date_for_slider.month

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "🌞 Solar Activity Dashboard - Interactive"

# Add auto-refresh interval for real-time updates
interval_component = dcc.Interval(
    id='interval-component',
    interval=30*1000,  # Update every 30 seconds
    n_intervals=0
)

# Beautiful Orange Theme Colors
colors = {
    'primary': '#FF6B35',
    'secondary': '#F7931E',
    'accent': '#FF8C42',
    'wheat': '#F5DEB3',
    'success': '#28A745',
    'danger': '#DC3545',
    'warning': '#FFC107',
    'info': '#17A2B8',
    'background': '#FFF8F0',
    'card': '#FFFFFF',
    'text': '#2C3E50',
    'text_secondary': '#6C757D',
    'border': '#E9ECEF',
}

# Ultimate Beautiful CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #FFF8F0 0%, #FFE4B5 15%, #FFDAB9 30%, #FFE4E1 45%, #FFF0F5 60%, #F0F8FF 75%, #E6F3FF 90%, #FFFFFF 100%);
                background-size: 400% 400%;
                animation: gradientShift 25s ease infinite;
                background-attachment: fixed;
                color: #2C3E50;
                min-height: 100vh;
                position: relative;
                overflow-x: hidden;
                font-weight: 400;
                line-height: 1.6;
                letter-spacing: -0.01em;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }
            
            @keyframes gradientShift {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
            
            body::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: 
                    radial-gradient(circle at 20% 20%, rgba(255, 107, 53, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(247, 147, 30, 0.15) 0%, transparent 50%),
                    radial-gradient(circle at 40% 60%, rgba(78, 205, 196, 0.1) 0%, transparent 50%),
                    radial-gradient(circle at 60% 40%, rgba(255, 200, 100, 0.1) 0%, transparent 50%);
                pointer-events: none;
                z-index: 0;
                animation: backgroundFloat 20s ease-in-out infinite;
            }
            
            @keyframes backgroundFloat {
                0%, 100% { transform: translateX(0) translateY(0) scale(1); }
                25% { transform: translateX(-30px) translateY(-20px) scale(1.05); }
                50% { transform: translateX(20px) translateY(30px) scale(0.95); }
                75% { transform: translateX(-10px) translateY(15px) scale(1.02); }
            }
            
            .ultimate-card {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(255, 248, 240, 0.95) 30%, rgba(255, 228, 196, 0.92) 60%, rgba(255, 218, 185, 0.88) 100%);
                backdrop-filter: blur(30px) saturate(130%);
                -webkit-backdrop-filter: blur(30px) saturate(130%);
                border: 1px solid rgba(255, 165, 0, 0.25);
                border-radius: 28px;
                box-shadow: 
                    0 20px 60px rgba(255, 140, 0, 0.12),
                    0 8px 25px rgba(255, 165, 0, 0.08),
                    0 3px 10px rgba(255, 140, 0, 0.06),
                    inset 0 1px 0 rgba(255, 255, 255, 0.9),
                    inset 0 -1px 0 rgba(255, 140, 0, 0.15);
                transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
                overflow: hidden;
                position: relative;
                animation: cardFloat 10s ease-in-out infinite;
            }
            
            @keyframes cardFloat {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-8px); }
            }
            
            .ultimate-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 5px;
                background: linear-gradient(90deg, #FF6B35 0%, #F7931E 50%, #FF8C42 100%);
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3);
            }
            
            .ultimate-card::after {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255, 107, 53, 0.05) 0%, transparent 70%);
                opacity: 0;
                transition: opacity 0.5s ease;
            }
            
            .ultimate-card:hover {
                transform: translateY(-18px) scale(1.04) rotateX(2deg);
                box-shadow: 
                    0 35px 80px rgba(255, 140, 0, 0.2),
                    0 15px 40px rgba(255, 165, 0, 0.12),
                    0 5px 15px rgba(255, 140, 0, 0.08),
                    inset 0 1px 0 rgba(255, 255, 255, 0.95),
                    0 0 0 1px rgba(255, 165, 0, 0.3);
                border-color: rgba(255, 165, 0, 0.4);
                animation: none;
            }
            
            .ultimate-card:hover::after {
                opacity: 1;
            }
            
            .chart-header {
                background: linear-gradient(135deg, #FF8C00 0%, #FFA500 25%, #FFB347 50%, #FFD700 75%, #FFF8DC 100%);
                background-size: 300% 300%;
                animation: gradientShift 8s ease infinite;
                color: #2C3E50;
                padding: 28px 36px;
                position: relative;
                overflow: hidden;
                text-align: center;
                border-radius: 28px 28px 0 0;
                box-shadow: 
                    0 10px 30px rgba(255, 140, 0, 0.25),
                    0 4px 12px rgba(255, 165, 0, 0.15),
                    inset 0 1px 0 rgba(255, 255, 255, 0.7),
                    inset 0 -1px 0 rgba(255, 140, 0, 0.2);
                font-weight: 600;
                letter-spacing: -0.02em;
            }
            
            .chart-header h5 {
                text-align: center;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .chart-header::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
                animation: shimmer 2.5s infinite;
            }
            
            .chart-header::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
                animation: pulse 4s ease-in-out infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 0.3; }
                50% { opacity: 0.8; }
            }
            
            @keyframes gradientShift {
                0%, 100% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
            }
            
            @keyframes shimmer {
                0% { left: -100%; }
                100% { left: 100%; }
            }
            
            /* Premium Loading Animation */
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                animation: fadeOut 2s ease-in-out 1s forwards;
            }
            
            .loading-spinner {
                width: 80px;
                height: 80px;
                border: 4px solid rgba(255, 255, 255, 0.3);
                border-top: 4px solid #FF6B35;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            @keyframes fadeOut {
                0% { opacity: 1; }
                100% { opacity: 0; visibility: hidden; }
            }
                border-radius: 20px 20px 0 0;
                font-weight: 700;
                font-size: 1.3rem;
                position: relative;
                overflow: hidden;
            }
            
            .chart-header::before {
                content: '';
                position: absolute;
                top: -50%;
                right: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
                animation: shimmer 4s ease-in-out infinite;
            }
            
            @keyframes shimmer {
                0%, 100% { transform: translateX(-100%) translateY(-100%) rotate(30deg); }
                50% { transform: translateX(100%) translateY(100%) rotate(30deg); }
            }
            
            .metric-card {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.3) 0%, rgba(255, 255, 255, 0.1) 100%);
                backdrop-filter: blur(30px) saturate(180%);
                -webkit-backdrop-filter: blur(30px) saturate(180%);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 24px;
                padding: 32px;
                box-shadow: 
                    0 20px 50px rgba(0, 0, 0, 0.1),
                    0 8px 20px rgba(255, 107, 53, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
                transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
                position: relative;
                overflow: hidden;
                animation: metricFloat 8s ease-in-out infinite;
            }
            
            @keyframes metricFloat {
                0%, 100% { transform: translateY(0px) scale(1); }
                50% { transform: translateY(-8px) scale(1.02); }
            }
            
            .metric-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #FF6B35, #F7931E);
            }
            
            .metric-card:hover {
                transform: translateY(-15px) scale(1.05) rotateX(3deg);
                box-shadow: 
                    0 30px 60px rgba(255, 107, 53, 0.3),
                    0 15px 30px rgba(0, 0, 0, 0.15),
                    inset 0 1px 0 rgba(255, 255, 255, 0.5);
                border-color: rgba(255, 255, 255, 0.4);
                animation: none;
            }
            
            .metric-icon {
                width: 80px;
                height: 80px;
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                font-size: 36px;
                color: white;
                background: linear-gradient(135deg, #FF6B35, #F7931E);
                position: relative;
                overflow: hidden;
            }
            
            .metric-icon::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(135deg, rgba(255,255,255,0.3) 0%, transparent 100%);
            }
            
            .metric-value {
                font-size: 3.2rem;
                font-weight: 800;
                background: linear-gradient(135deg, #FF6B35, #F7931E);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 10px;
            }
            
            .metric-label {
                font-size: 1rem;
                font-weight: 600;
                color: #6C757D;
                text-transform: uppercase;
                letter-spacing: 1.5px;
            }
            
            .section-title {
                font-size: 2.2rem;
                font-weight: 800;
                color: #2C3E50;
                margin-bottom: 2.5rem;
                text-align: center;
                position: relative;
                width: 100%;
            }
            
            .section-title::before {
                content: '';
                position: absolute;
                left: 0;
                top: 50%;
                transform: translateY(-50%);
                width: 6px;
                height: 50px;
                background: linear-gradient(135deg, #FF6B35, #F7931E);
                border-radius: 3px;
            }
            
            .filter-section {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border: 2px solid rgba(255, 107, 53, 0.3);
                border-radius: 20px;
                padding: 32px;
                margin-bottom: 2.5rem;
                box-shadow: 0 10px 40px rgba(255, 107, 53, 0.12);
            }
            
            .filter-group {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 248, 240, 0.9) 100%);
                border: 2px solid rgba(255, 107, 53, 0.3);
                border-radius: 16px;
                padding: 18px;
                margin-bottom: 0;
                transition: all 0.3s ease;
                height: 100%;
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.08);
            }
            
            .filter-group:hover {
                background: linear-gradient(135deg, rgba(255, 255, 255, 1) 0%, rgba(255, 248, 240, 1) 100%);
                border-color: rgba(255, 107, 53, 0.5);
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(255, 107, 53, 0.12);
            }
            
            .selector-label {
                font-size: 0.85rem;
                font-weight: 700;
                color: #FF6B35;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .filter-icon-label {
                display: flex;
                align-items: center;
                margin-bottom: 14px;
                padding-bottom: 8px;
                border-bottom: 2px solid rgba(255, 107, 53, 0.2);
            }
            
            .filter-icon-label i {
                font-size: 1.1rem;
                color: #FF6B35;
                margin-right: 10px;
                padding: 6px;
                background: rgba(255, 107, 53, 0.1);
                border-radius: 8px;
            }
            
            .filter-icon-label label {
                font-size: 0.95rem;
                font-weight: 700;
                color: #2C3E50;
                margin: 0;
            }
            
            /* Ultra Professional DatePicker styling */
            .DateInput_input {
                font-size: 1rem !important;
                font-weight: 700 !important;
                color: #2C3E50 !important;
                border: 3px solid rgba(255, 107, 53, 0.4) !important;
                border-radius: 12px !important;
                padding: 14px 18px !important;
                background: linear-gradient(135deg, #ffffff 0%, #fff8f0 100%) !important;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.1) !important;
            }
            
            .DateInput_input:hover {
                border-color: rgba(255, 107, 53, 0.7) !important;
                box-shadow: 0 6px 16px rgba(255, 107, 53, 0.15) !important;
                transform: translateY(-2px) !important;
            }
            
            .DateInput_input:focus {
                border-color: #FF6B35 !important;
                box-shadow: 0 0 0 5px rgba(255, 107, 53, 0.2), 0 8px 20px rgba(255, 107, 53, 0.2) !important;
                outline: none !important;
                transform: translateY(-2px) !important;
            }
            
            /* Professional Calendar Dropdown styling */
            .DateRangePickerInput {
                background: linear-gradient(135deg, #ffffff 0%, #fff8f0 100%) !important;
                border-radius: 12px !important;
                box-shadow: 0 6px 20px rgba(255, 107, 53, 0.15) !important;
                border: 3px solid rgba(255, 107, 53, 0.3) !important;
            }
            
            .DateRangePickerInput:hover {
                box-shadow: 0 8px 24px rgba(255, 107, 53, 0.2) !important;
            }
            
            .DateRangePickerInput_arrow {
                color: #FF6B35 !important;
                font-size: 1.4rem !important;
                font-weight: 700 !important;
                transition: all 0.3s ease !important;
            }
            
            .DateRangePickerInput_arrow:hover {
                transform: scale(1.2) !important;
            }
            
            /* Override any React DayPicker styles */
            .DayPicker {
                background: white !important;
            }
            
            .DayPicker-Day {
                background: white !important;
                color: #2C3E50 !important;
            }
            
            .DayPicker-Day:hover {
                background: rgba(255, 107, 53, 0.2) !important;
            }
            
            .DayPicker-Day--selected {
                background: linear-gradient(135deg, #FF6B35, #F7931E) !important;
                color: white !important;
            }
            
            .DayPicker-Day--today {
                background: rgba(255, 107, 53, 0.25) !important;
                color: #FF6B35 !important;
                border: 3px solid #FF6B35 !important;
            }
            
            /* Ultra Professional Calendar DayPicker styling */
            .Calendar {
                border: 4px solid rgba(255, 107, 53, 0.3) !important;
                border-radius: 20px !important;
                box-shadow: 0 20px 60px rgba(255, 107, 53, 0.25) !important;
                overflow: hidden !important;
                background: white !important;
                position: relative !important;
            }
            
            .Calendar::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #FF6B35, #F7931E, #FF8C42);
                z-index: 10;
            }
            
            .Calendar__header {
                background: linear-gradient(135deg, #FF6B35 0%, #F7931E 50%, #FF8C42 100%) !important;
                color: white !important;
                padding: 20px !important;
                font-weight: 900 !important;
                font-size: 1.2rem !important;
                position: relative !important;
                overflow: hidden !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
            }
            
            .Calendar__header::before {
                content: '';
                position: absolute;
                top: -50%;
                right: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.25) 0%, transparent 70%);
                animation: shimmer 3s ease-in-out infinite;
            }
            
            .Calendar__navigation {
                color: white !important;
                font-size: 1.5rem !important;
                font-weight: 800 !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                background: rgba(255, 255, 255, 0.1) !important;
                border-radius: 50% !important;
                width: 40px !important;
                height: 40px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            
            .Calendar__navigation:hover {
                transform: scale(1.15) rotate(5deg) !important;
                background: rgba(255, 255, 255, 0.2) !important;
            }
            
            .Calendar__day {
                color: #2C3E50 !important;
                font-weight: 700 !important;
                font-size: 1rem !important;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
                border-radius: 10px !important;
                margin: 3px !important;
                position: relative !important;
                background: white !important;
            }
            
            .Calendar__day::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                border-radius: 10px;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .Calendar__day:hover {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.2), rgba(247, 147, 30, 0.2)) !important;
                transform: scale(1.15) !important;
                font-weight: 800 !important;
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3) !important;
            }
            
            .Calendar__day:hover::before {
                opacity: 1;
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.1), rgba(247, 147, 30, 0.1));
            }
            
            .Calendar__day--today {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.25), rgba(247, 147, 30, 0.25)) !important;
                color: #FF6B35 !important;
                font-weight: 900 !important;
                border: 3px solid #FF6B35 !important;
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3) !important;
            }
            
            .Calendar__day--selected {
                background: linear-gradient(135deg, #FF6B35, #F7931E) !important;
                color: white !important;
                font-weight: 900 !important;
                box-shadow: 0 6px 20px rgba(255, 107, 53, 0.5) !important;
                transform: scale(1.1) !important;
                border: 2px solid white !important;
            }
            
            .Calendar__day--blocked {
                color: #C0C0C0 !important;
                cursor: not-allowed !important;
                opacity: 0.4 !important;
                background: #F5F5F5 !important;
            }
            
            /* Override any default calendar backgrounds */
            .Calendar__table td {
                background: white !important;
            }
            
            .Calendar__month,
            .Calendar__monthPicker {
                background: white !important;
            }
            
            .Calendar__monthPicker {
                background: white !important;
            }
            
            /* Ensure no teal colors appear */
            td.Calendar__day,
            .Calendar__day.Calendar__day_1,
            .Calendar__day.Calendar__day_2,
            .Calendar__day.Calendar__day_3,
            .Calendar__day.Calendar__day_4,
            .Calendar__day.Calendar__day_5,
            .Calendar__day.Calendar__day_6,
            .Calendar__day.Calendar__day_7,
            .Calendar__day.Calendar__day_8,
            .Calendar__day.Calendar__day_9,
            .Calendar__day.Calendar__day_10,
            .Calendar__day.Calendar__day_11,
            .Calendar__day.Calendar__day_12,
            .Calendar__day.Calendar__day_13,
            .Calendar__day.Calendar__day_14,
            .Calendar__day.Calendar__day_15,
            .Calendar__day.Calendar__day_16,
            .Calendar__day.Calendar__day_17,
            .Calendar__day.Calendar__day_18,
            .Calendar__day.Calendar__day_19,
            .Calendar__day.Calendar__day_20,
            .Calendar__day.Calendar__day_21,
            .Calendar__day.Calendar__day_22,
            .Calendar__day.Calendar__day_23,
            .Calendar__day.Calendar__day_24,
            .Calendar__day.Calendar__day_25,
            .Calendar__day.Calendar__day_26,
            .Calendar__day.Calendar__day_27,
            .Calendar__day.Calendar__day_28,
            .Calendar__day.Calendar__day_29,
            .Calendar__day.Calendar__day_30,
            .Calendar__day.Calendar__day_31 {
                background: white !important;
                color: #2C3E50 !important;
            }
            
            .Calendar__weekdays {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.1), rgba(247, 147, 30, 0.1)) !important;
                color: #FF6B35 !important;
                font-weight: 800 !important;
                padding: 14px 0 !important;
                font-size: 0.95rem !important;
                text-transform: uppercase !important;
                letter-spacing: 1px !important;
            }
            
            .Calendar__monthSelector,
            .Calendar__yearSelector {
                background: white !important;
                border: 3px solid rgba(255, 107, 53, 0.25) !important;
                border-radius: 16px !important;
                box-shadow: 0 8px 24px rgba(255, 107, 53, 0.2) !important;
            }
            
            .Calendar__monthOption:hover,
            .Calendar__yearOption:hover {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.2), rgba(247, 147, 30, 0.2)) !important;
                color: #FF6B35 !important;
                font-weight: 800 !important;
                transform: scale(1.05) !important;
            }
            
            .Calendar__monthOption--selected,
            .Calendar__yearOption--selected {
                background: linear-gradient(135deg, #FF6B35, #F7931E) !important;
                color: white !important;
                font-weight: 900 !important;
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4) !important;
            }
            
            /* Override all calendar cell backgrounds */
            table.Calendar__table tbody tr td {
                background: white !important;
            }
            
            /* Prevent any teal/aqua colors */
            * {
                --teal-color: #FF6B35 !important;
                --aqua-color: #F7931E !important;
            }
            
            /* Ensure all calendar dates are white with orange theme */
            .SingleDatePickerInput__withBorder,
            .DateRangePickerInput__withBorder {
                border-color: rgba(255, 107, 53, 0.3) !important;
            }
            
            /* Custom Checklist styling */
            .form-check-input {
                width: 20px !important;
                height: 20px !important;
                border: 2px solid rgba(255, 107, 53, 0.3) !important;
                border-radius: 6px !important;
                transition: all 0.3s ease !important;
                cursor: pointer !important;
            }
            
            .form-check-input:hover {
                border-color: rgba(255, 107, 53, 0.6) !important;
                transform: scale(1.1) !important;
            }
            
            .form-check-input:checked {
                background: linear-gradient(135deg, #FF6B35, #F7931E) !important;
                border-color: #FF6B35 !important;
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3) !important;
            }
            
            .form-check-input:focus {
                border-color: #FF6B35 !important;
                box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.2) !important;
            }
            
            .form-check-label {
                font-size: 0.95rem !important;
                font-weight: 600 !important;
                color: #2C3E50 !important;
                margin-left: 10px !important;
                cursor: pointer !important;
                transition: color 0.2s ease !important;
            }
            
            .form-check-label:hover {
                color: #FF6B35 !important;
            }
            
            /* Improve checklist container */
            ._input-container {
                padding: 8px 0 !important;
            }
            
            /* Custom Dropdown styling */
            .Select-control {
                border: 2px solid rgba(255, 107, 53, 0.3) !important;
                border-radius: 12px !important;
                background: linear-gradient(135deg, #ffffff 0%, #fff8f0 100%) !important;
                padding: 4px 8px !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.1) !important;
            }
            
            .Select-control:hover {
                border-color: rgba(255, 107, 53, 0.5) !important;
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.15) !important;
                transform: translateY(-1px) !important;
            }
            
            .is-focused .Select-control {
                border-color: #FF6B35 !important;
                box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.15), 0 4px 12px rgba(255, 107, 53, 0.2) !important;
            }
            
            .Select-menu-outer {
                border: 2px solid rgba(255, 107, 53, 0.3) !important;
                border-radius: 12px !important;
                box-shadow: 0 8px 24px rgba(255, 107, 53, 0.2) !important;
                backdrop-filter: blur(10px) !important;
                background: rgba(255, 255, 255, 0.98) !important;
            }
            
            .Select-option {
                padding: 12px 16px !important;
                transition: all 0.2s ease !important;
                border-radius: 8px !important;
                margin: 4px !important;
            }
            
            .Select-option:hover {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.15), rgba(247, 147, 30, 0.15)) !important;
                transform: translateX(4px) !important;
            }
            
            .Select-option.is-selected {
                background: linear-gradient(135deg, #FF6B35, #F7931E) !important;
                color: white !important;
                font-weight: 700 !important;
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3) !important;
            }
            
            .header-gradient {
                background: linear-gradient(135deg, #FF6B35, #F7931E, #FF8C42);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                 text-shadow: 0 0 20px rgba(255, 107, 53, 0.5),
                             0 0 40px rgba(255, 107, 53, 0.3),
                             0 0 60px rgba(255, 107, 53, 0.2);
                 animation: glowPulse 3s ease-in-out infinite;
             }
             
             @keyframes glowPulse {
                 0%, 100% {
                     text-shadow: 0 0 10px rgba(255, 215, 0, 0.25),
                                 0 0 20px rgba(255, 215, 0, 0.15),
                                 0 0 30px rgba(255, 215, 0, 0.1);
                 }
                 50% {
                     text-shadow: 0 0 18px rgba(255, 215, 0, 0.4),
                                 0 0 35px rgba(255, 215, 0, 0.25),
                                 0 0 50px rgba(255, 215, 0, 0.15);
                 }
             }
             
             .project-title {
                font-size: 5rem;
                 font-weight: 900;
                background: linear-gradient(135deg, #FF6B35 0%, #F7931E 25%, #FF8C42 50%, #FFB366 75%, #FFD700 100%);
                background-size: 300% 300%;
                 -webkit-background-clip: text;
                 -webkit-text-fill-color: transparent;
                 background-clip: text;
                text-shadow: 0 0 20px rgba(255, 215, 0, 0.4),
                            0 0 40px rgba(255, 215, 0, 0.3),
                            0 0 60px rgba(255, 215, 0, 0.2);
                animation: glowPulse 3s ease-in-out infinite, gradientShift 6s ease infinite;
                letter-spacing: 4px;
                filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.3));
                position: relative;
                text-transform: uppercase;
             }
             
             .project-subtitle {
                 font-size: 1.8rem;
                 font-weight: 700;
                 color: #2C3E50;
                 letter-spacing: 2px;
                 text-transform: uppercase;
                 animation: fadeInGlow 2s ease-in-out;
             }
             
             @keyframes fadeInGlow {
                 0% {
                     opacity: 0;
                     transform: translateY(-20px);
                 }
                 100% {
                     opacity: 1;
                     transform: translateY(0);
                 }
             }
            
            /* Premium Metric Cards - Transparent Glassmorphic with Animations */
            .metric-card {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 248, 240, 0.92) 30%, rgba(255, 228, 196, 0.88) 60%, rgba(255, 218, 185, 0.85) 100%);
                backdrop-filter: blur(25px) saturate(120%);
                -webkit-backdrop-filter: blur(25px) saturate(120%);
                border: 1px solid rgba(255, 165, 0, 0.3);
                border-radius: 28px;
                padding: 36px 28px;
                box-shadow: 
                    0 15px 40px rgba(255, 140, 0, 0.15),
                    0 6px 18px rgba(255, 165, 0, 0.1),
                    0 2px 8px rgba(255, 140, 0, 0.06),
                    inset 0 1px 0 rgba(255, 255, 255, 0.95),
                    inset 0 -1px 0 rgba(255, 140, 0, 0.2);
                transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
                position: relative;
                overflow: hidden;
                animation: fadeInUp 1s ease-out forwards;
                opacity: 0;
            }
            
            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            /* Stagger animation for each card */
            .metric-card:nth-child(1) { animation-delay: 0.1s; }
            .metric-card:nth-child(2) { animation-delay: 0.2s; }
            .metric-card:nth-child(3) { animation-delay: 0.3s; }
            .metric-card:nth-child(4) { animation-delay: 0.4s; }
            .metric-card:nth-child(5) { animation-delay: 0.5s; }
            .metric-card:nth-child(6) { animation-delay: 0.6s; }
            
            .metric-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 5px;
                background: linear-gradient(90deg, #FF6B35, #F7931E, #FF8C42, #FF6B35);
                background-size: 200% 100%;
                animation: gradientShift 3s ease infinite, pulseGlow 2s ease-in-out infinite;
                box-shadow: 0 2px 12px rgba(255, 107, 53, 0.4);
            }
            
            @keyframes pulseGlow {
                0%, 100% { box-shadow: 0 2px 12px rgba(255, 107, 53, 0.4); }
                50% { box-shadow: 0 2px 20px rgba(255, 107, 53, 0.7); }
            }
            
            .metric-card::after {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255, 107, 53, 0.08) 0%, transparent 70%);
                opacity: 0;
                transition: opacity 0.5s ease;
                animation: rotate 15s linear infinite;
            }
            
            @keyframes rotate {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            
            .metric-card:hover {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.55) 0%, rgba(255, 248, 240, 0.5) 100%);
                border-color: rgba(255, 107, 53, 0.6);
                transform: translateY(-20px) scale(1.06) rotate(1deg);
                box-shadow: 
                    0 30px 80px rgba(255, 107, 53, 0.4),
                    0 15px 30px rgba(0, 0, 0, 0.15),
                    inset 0 1px 0 rgba(255, 255, 255, 0.95),
                    inset 0 -1px 0 rgba(255, 107, 53, 0.3),
                    0 0 30px rgba(255, 107, 53, 0.2);
                cursor: pointer;
            }
            
            .metric-card:hover::after {
                opacity: 1;
                animation: rotate 10s linear infinite;
            }
            
            .metric-card:hover::before {
                animation: gradientShift 1s ease infinite, pulseGlow 0.8s ease-in-out infinite;
                height: 6px;
                box-shadow: 0 3px 20px rgba(255, 107, 53, 0.6);
            }
            
            .title-gradient {
                color: #FF6B35 !important;
                font-weight: 800 !important;
                font-size: 0.95rem !important;
                letter-spacing: 1px;
                margin-bottom: 16px !important;
                text-transform: uppercase;
                transition: all 0.3s ease;
                display: block !important;
                position: relative;
                width: 100%;
                text-align: center;
            }
            
            .title-gradient::after {
                content: '';
                position: absolute;
                bottom: -4px;
                left: 0;
                width: 0;
                height: 2px;
                background: linear-gradient(90deg, #FF6B35, #F7931E);
                transition: width 0.3s ease;
            }
            
            .metric-card:hover .title-gradient {
                color: #F7931E !important;
                font-size: 1rem !important;
                letter-spacing: 1.2px;
            }
            
            .metric-card:hover .title-gradient::after {
                width: 100%;
                height: 3px;
            }
            
            .value-gradient {
                color: #2C3E50 !important;
                font-weight: 900 !important;
                font-size: 3rem !important;
                margin: 16px 0 !important;
                letter-spacing: -1px;
                text-shadow: 0 3px 6px rgba(0, 0, 0, 0.08);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                display: block !important;
                animation: valueAppear 0.8s ease-out forwards;
                width: 100%;
                text-align: center;
            }
            
            @keyframes valueAppear {
                from {
                    opacity: 0;
                    transform: scale(0.5);
                }
                to {
                    opacity: 1;
                    transform: scale(1);
                }
            }
            
            .metric-card:hover .value-gradient {
                color: #FF6B35 !important;
                transform: scale(1.1);
                text-shadow: 0 5px 15px rgba(255, 107, 53, 0.4);
                animation: valuePulse 1.2s ease-in-out infinite;
                font-size: 3.2rem !important;
            }
            
            @keyframes valuePulse {
                0%, 100% { transform: scale(1.1); }
                50% { transform: scale(1.15); }
            }
            
            /* All KPIs have uniform styling for consistency */
            
            .metric-card .text-center {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                width: 100%;
            }
            
            .icon-gradient {
                color: #FF6B35 !important;
                font-size: 3.2rem !important;
                margin-bottom: 20px !important;
                filter: drop-shadow(0 4px 10px rgba(255, 107, 53, 0.35));
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                display: block !important;
                position: relative;
                z-index: 1;
                animation: iconFloat 3s ease-in-out infinite;
                width: 100%;
                text-align: center;
            }
            
            @keyframes iconFloat {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-8px); }
            }
            
            .icon-gradient::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 70px;
                height: 70px;
                background: radial-gradient(circle, rgba(255, 107, 53, 0.2) 0%, transparent 70%);
                border-radius: 50%;
                opacity: 0;
                transition: opacity 0.3s ease;
                animation: pulseRing 2s ease-out infinite;
            }
            
            @keyframes pulseRing {
                0% {
                    transform: translate(-50%, -50%) scale(0.8);
                    opacity: 0.8;
                }
                100% {
                    transform: translate(-50%, -50%) scale(1.3);
                    opacity: 0;
                }
            }
            
            .metric-card:hover .icon-gradient {
                transform: scale(1.3) rotate(12deg);
                filter: drop-shadow(0 12px 25px rgba(255, 107, 53, 0.7));
                animation: iconBounce 0.8s ease;
                color: #F7931E !important;
            }
            
            @keyframes iconBounce {
                0%, 100% { transform: scale(1.3) rotate(12deg); }
                50% { transform: scale(1.4) rotate(15deg); }
            }
            
            .metric-card:hover .icon-gradient::before {
                opacity: 1;
                width: 90px;
                height: 90px;
            }
            
            .text-muted {
                color: #FF6B35 !important;
                font-weight: 700 !important;
                font-size: 0.9rem !important;
                letter-spacing: 0.5px;
                opacity: 0.85;
                transition: all 0.3s ease;
                display: inline-block;
                position: relative;
            }
            
            .text-muted::before {
                content: '';
                position: absolute;
                left: -8px;
                top: 50%;
                transform: translateY(-50%);
                width: 4px;
                height: 4px;
                background: #FF6B35;
                border-radius: 50%;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .metric-card:hover .text-muted {
                opacity: 1;
                transform: translateY(-3px);
                letter-spacing: 0.8px;
            }
            
            .metric-card:hover .text-muted::before {
                opacity: 1;
                animation: dotPulse 1s ease-in-out infinite;
            }
            
            @keyframes dotPulse {
                0%, 100% { transform: translateY(-50%) scale(1); }
                50% { transform: translateY(-50%) scale(1.3); }
            }
            
            /* Sidebar Enhancement */
            .side-panel-header {
                background: linear-gradient(135deg, #FF6B35 0%, #F7931E 50%, #FF8C42 100%);
                background-size: 200% 200%;
                animation: gradientShift 8s ease infinite;
                padding: 20px 24px;
                color: white;
                font-weight: 900;
                font-size: 1.15rem;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                position: relative;
                overflow: hidden;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 6px 20px rgba(255, 107, 53, 0.25);
                border-bottom: 3px solid rgba(255, 255, 255, 0.2);
            }
            
            .side-panel-header i {
                filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.3));
                animation: pulseIcon 2s ease-in-out infinite;
            }
            
            @keyframes pulseIcon {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }
            
            .side-panel-header::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                animation: shimmer 3s infinite;
            }
            
            .side-panel-header::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
            }
            
            /* Premium Filter Groups */
            .side-panel-filter-group {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(255, 248, 240, 0.95) 100%);
                backdrop-filter: blur(25px) saturate(180%);
                border: 2px solid rgba(255, 107, 53, 0.15);
                border-radius: 24px;
                padding: 28px;
                margin-bottom: 28px;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 
                    0 8px 24px rgba(255, 107, 53, 0.08),
                    0 4px 12px rgba(0, 0, 0, 0.04),
                    inset 0 1px 0 rgba(255, 255, 255, 0.7);
                position: relative;
                overflow: hidden;
            }
            
            .side-panel-filter-group::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #FF6B35, #F7931E, #FF8C42);
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .side-panel-filter-group:hover {
                border-color: rgba(255, 107, 53, 0.35);
                box-shadow: 
                    0 12px 32px rgba(255, 107, 53, 0.18),
                    0 6px 16px rgba(0, 0, 0, 0.06),
                    inset 0 1px 0 rgba(255, 255, 255, 0.9);
                transform: translateY(-6px) scale(1.02);
            }
            
            .side-panel-filter-group:hover::before {
                opacity: 1;
            }
            
            .side-panel-icon-label {
                display: flex;
                align-items: center;
                gap: 14px;
                margin-bottom: 20px;
                padding-bottom: 14px;
                border-bottom: 2px solid rgba(255, 107, 53, 0.12);
                position: relative;
            }
            
            .side-panel-icon-label::after {
                content: '';
                position: absolute;
                bottom: -2px;
                left: 0;
                width: 0;
                height: 2px;
                background: linear-gradient(90deg, #FF6B35, #F7931E);
                transition: width 0.3s ease;
            }
            
            .side-panel-filter-group:hover .side-panel-icon-label::after {
                width: 100%;
            }
            
            .side-panel-icon-label i {
                color: #FF6B35;
                font-size: 1.25rem;
                min-width: 44px;
                min-height: 44px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.12), rgba(247, 147, 30, 0.12));
                border-radius: 12px;
                padding: 10px;
                box-shadow: 0 3px 10px rgba(255, 107, 53, 0.12);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                border: 1px solid rgba(255, 107, 53, 0.1);
            }
            
            .side-panel-icon-label:hover i {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.2), rgba(247, 147, 30, 0.2));
                transform: scale(1.1) rotate(5deg);
                box-shadow: 0 6px 16px rgba(255, 107, 53, 0.25);
                border-color: rgba(255, 107, 53, 0.2);
            }
            
            .side-panel-icon-label label {
                font-weight: 900;
                font-size: 1.05rem;
                color: #2C3E50;
                letter-spacing: 1px;
                text-transform: uppercase;
                flex: 1;
                margin: 0;
                transition: all 0.2s ease;
            }
            
            .side-panel-icon-label:hover label {
                color: #FF6B35;
                letter-spacing: 1.2px;
            }
            
            /* Polish all paragraph labels in sidebar */
            .side-panel-filter-group p {
                font-weight: 800 !important;
                letter-spacing: 0.8px !important;
                margin-bottom: 14px !important;
                transition: all 0.2s ease !important;
                font-size: 0.85rem !important;
                text-transform: uppercase !important;
            }
            
            .side-panel-filter-group p:hover {
                color: #FF6B35 !important;
                letter-spacing: 1px !important;
            }
            
            /* Enhanced Checklist styling */
            .side-panel-filter-group .rc-form-check {
                padding: 8px 12px;
                margin: 4px 0;
                border-radius: 10px;
                transition: all 0.3s ease;
                background: rgba(255, 107, 53, 0.03);
                border: 1px solid rgba(255, 107, 53, 0.08);
            }
            
            .side-panel-filter-group .rc-form-check:hover {
                background: rgba(255, 107, 53, 0.08);
                border-color: rgba(255, 107, 53, 0.2);
                transform: translateX(4px);
            }
            
            .side-panel-filter-group .rc-form-check input:checked + label {
                color: #FF6B35;
                font-weight: 700;
            }
            
            .side-panel-filter-group .rc-form-check label {
                font-size: 0.95rem;
                color: #2C3E50;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .side-panel-filter-group .rc-form-check:hover label {
                color: #FF6B35;
            }
            
            /* Premium Chart Containers */
            .chart-container-wrapper {
                padding: 24px;
                background: rgba(255, 255, 255, 0.5);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                border: 1px solid rgba(255, 107, 53, 0.1);
                box-shadow: 0 4px 16px rgba(255, 107, 53, 0.05);
            }
            
            /* Tooltip Enhancement */
            .js-plotly-plot .plotly .modebar {
                background: rgba(255, 255, 255, 0.9) !important;
                backdrop-filter: blur(10px);
                border-radius: 8px;
                border: 1px solid rgba(255, 107, 53, 0.2);
            }
            
            /* Summary Card Enhancement */
            .summary-card {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.06) 0%, rgba(247, 147, 30, 0.06) 100%);
                border: 2px solid rgba(255, 107, 53, 0.15);
                border-radius: 18px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 6px 20px rgba(255, 107, 53, 0.1);
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .summary-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: linear-gradient(90deg, #FF6B35, #F7931E);
            }
            
            .summary-card:hover {
                border-color: rgba(255, 107, 53, 0.3);
                box-shadow: 0 8px 24px rgba(255, 107, 53, 0.15);
                transform: translateY(-2px);
            }
            
            .summary-title {
                color: #FF6B35;
                font-weight: 800;
                font-size: 0.95rem;
                text-transform: uppercase;
                letter-spacing: 1.2px;
                margin-bottom: 14px;
            }
            
            .summary-item {
                padding: 10px 14px;
                margin-bottom: 8px;
                background: rgba(255, 255, 255, 0.7);
                border-radius: 10px;
                border-left: 3px solid #FF6B35;
                transition: all 0.2s ease;
            }
            
            .summary-item:hover {
                background: rgba(255, 255, 255, 0.9);
                transform: translateX(4px);
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.1);
            }
            
            .summary-item strong {
                color: #FF6B35;
                font-weight: 800;
            }
            
            .summary-item:last-child {
                margin-bottom: 0;
            }
            
            /* Side Panel Styles - Merged */
            .side-panel {
                position: fixed;
                left: 0;
                top: 0;
                width: 380px;
                height: 100vh;
                background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(255, 255, 255, 0.95) 100%);
                backdrop-filter: blur(30px) saturate(180%);
                border-right: 1px solid rgba(255, 107, 53, 0.15);
                box-shadow: 
                    4px 0 24px rgba(255, 107, 53, 0.08),
                    inset -1px 0 0 rgba(255, 255, 255, 0.5);
                overflow-y: auto;
                overflow-x: hidden;
                z-index: 1000;
                padding: 0;
                transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .side-panel::-webkit-scrollbar {
                width: 8px;
            }
            
            .side-panel::-webkit-scrollbar-track {
                background: rgba(255, 107, 53, 0.05);
                border-radius: 10px;
            }
            
            .side-panel::-webkit-scrollbar-thumb {
                background: linear-gradient(135deg, #FF6B35, #F7931E);
                border-radius: 10px;
            }
            
            .side-panel::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(135deg, #F7931E, #FF8C42);
            }
            
            .side-panel-collapsed {
                transform: translateX(-100%);
            }
            
            
            .side-panel-content {
                padding: 28px 24px;
                min-height: calc(100vh - 70px);
                overflow-y: auto;
                overflow-x: hidden;
            }
            
            .side-panel-content::-webkit-scrollbar {
                width: 8px;
            }
            
            .side-panel-content::-webkit-scrollbar-track {
                background: rgba(255, 107, 53, 0.05);
                border-radius: 10px;
            }
            
            .side-panel-content::-webkit-scrollbar-thumb {
                background: linear-gradient(135deg, #FF6B35, #F7931E);
                border-radius: 10px;
            }
            
            .side-panel-content::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(135deg, #F7931E, #FF6B35);
            }
            
            .main-content-wrapper {
                margin-left: 380px;
                padding: 2rem;
                transition: margin-left 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .main-content-wrapper-expanded {
                margin-left: 0;
            }
            
            .panel-toggle-btn {
                position: fixed;
                left: 400px;
                top: 24px;
                z-index: 1001;
                background: linear-gradient(135deg, #FF6B35, #F7931E);
                color: white;
                border: none;
                border-radius: 50%;
                width: 52px;
                height: 52px;
                cursor: pointer;
                box-shadow: 0 6px 20px rgba(255, 107, 53, 0.35);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.3rem;
            }
            
            .panel-toggle-btn:hover {
                transform: scale(1.1) rotate(180deg);
                box-shadow: 0 8px 25px rgba(255, 107, 53, 0.45);
            }
            
            .panel-toggle-btn-collapsed {
                left: 20px;
            }
            
            .side-panel-filter-group {
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 248, 240, 0.9) 100%);
                border: 2px solid rgba(255, 107, 53, 0.3);
                border-radius: 16px;
                padding: 20px;
                margin-bottom: 20px;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.08);
            }
            
            .side-panel-filter-group:hover {
                background: linear-gradient(135deg, rgba(255, 255, 255, 1) 0%, rgba(255, 248, 240, 1) 100%);
                border-color: rgba(255, 107, 53, 0.5);
                transform: translateX(4px);
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.15);
            }
            
            .side-panel-icon-label {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 2px solid rgba(255, 107, 53, 0.15);
            }
            
            .side-panel-icon-label i {
                color: #FF6B35;
                font-size: 1.2rem;
                min-width: 40px;
                min-height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.1), rgba(247, 147, 30, 0.1));
                border-radius: 10px;
                padding: 8px;
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.1);
                transition: all 0.3s ease;
            }
            
            .side-panel-icon-label:hover i {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.2), rgba(247, 147, 30, 0.2));
                transform: scale(1.1);
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.2);
            }
            
            .side-panel-icon-label label {
                font-size: 1rem;
                font-weight: 700;
                color: #2C3E50;
                margin: 0;
                flex: 1;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }
            
            /* Professional Date Picker Container */
            .professional-date-picker {
                border-radius: 12px !important;
                width: 100% !important;
                position: relative !important;
            }
            
            .professional-date-picker .DateInput {
                border-radius: 12px !important;
                width: 100% !important;
                position: relative !important;
            }
            
            /* Container for proper calendar alignment */
            .professional-date-picker > div {
                position: relative !important;
                width: 100% !important;
            }
            
            .professional-date-picker .DateInput_input {
                border-radius: 12px !important;
                border: 2px solid rgba(255, 107, 53, 0.3) !important;
                padding: 14px 18px !important;
                font-size: 0.95rem !important;
                font-weight: 600 !important;
                background: linear-gradient(135deg, #ffffff 0%, #fff8f0 100%) !important;
                color: #2C3E50 !important;
                width: 100% !important;
                box-sizing: border-box !important;
            }
            
            .professional-date-picker .DateInput_input:hover {
                border-color: rgba(255, 107, 53, 0.6) !important;
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.15) !important;
                transform: translateY(-1px) !important;
            }
            
            .professional-date-picker .DateInput_input:focus {
                border-color: #FF6B35 !important;
                box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.2) !important;
                outline: none !important;
            }
            
            /* SingleDatePicker styling */
            .SingleDatePicker {
                width: 100% !important;
                position: relative !important;
            }
            
            .SingleDatePickerInput {
                width: 100% !important;
                border-radius: 12px !important;
                position: relative !important;
            }
            
            .SingleDatePickerInput__withBorder {
                border: none !important;
            }
            
            /* Calendar popup styling */
            .DateRangePicker_picker,
            .SingleDatePicker_picker {
                border-radius: 20px !important;
                border: 3px solid rgba(255, 107, 53, 0.4) !important;
                box-shadow: 0 20px 60px rgba(255, 107, 53, 0.35) !important;
                overflow: visible !important;
                position: fixed !important;
                z-index: 999999 !important;
                background: white !important;
                padding: 12px !important;
                min-width: 320px !important;
            }
            
            /* Fix calendar alignment */
            .DatePicker__input-container {
                position: relative !important;
            }
            
            .SingleDatePickerInput {
                position: relative !important;
            }
            
            /* Ensure calendar is properly aligned */
            .DatePicker .SingleDatePicker_picker,
            .DatePicker .DateRangePicker_picker {
                left: 0 !important;
                right: auto !important;
                margin-left: 0 !important;
            }
            
            /* Fix calendar popup positioning */
            .DatePicker .SingleDatePicker_picker__openDown,
            .DatePicker .DateRangePicker_picker__openDown {
                left: 0 !important;
                transform: none !important;
            }
            
            /* Calendar positioning relative to input */
            .SingleDatePickerInput .SingleDatePicker_picker,
            .DateRangePickerInput .DateRangePicker_picker {
                position: fixed !important;
                left: 0 !important;
                bottom: auto !important;
                top: auto !important;
                margin-bottom: 50px !important;
                z-index: 999999 !important;
            }
            
            /* Force proper alignment for all date picker containers */
            .dash-datepicker-single-container {
                position: relative !important;
                width: 100% !important;
            }
            
            .dash-datepicker-single-container > div {
                position: relative !important;
                width: 100% !important;
            }
            
            /* Ensure calendar dropdown aligns to container left edge */
            .dash-datepicker-single-container .SingleDatePicker_picker,
            .dash-datepicker-single-container .DateRangePicker_picker {
                left: 0 !important;
                margin-left: 0 !important;
                transform: none !important;
            }
            
            /* Override any right alignment */
            .SingleDatePicker_picker,
            .DateRangePicker_picker {
                left: 0 !important;
                right: auto !important;
                margin-left: 0 !important;
                margin-right: auto !important;
            }
            
            /* Container alignment wrapper */
            .professional-date-picker-container {
                position: relative !important;
                width: 100% !important;
                overflow: visible !important;
                z-index: 1000 !important;
            }
            
            /* Hide end date wrapper when start date calendar is open */
            .side-panel-filter-group:has(.SingleDatePicker_picker__openDown) #end-date-wrapper {
                display: none !important;
            }
            
            /* Alternative selector for when calendar is open */
            .professional-date-picker-container:has(.SingleDatePicker_picker__openDown) ~ div #end-date-wrapper {
                display: none !important;
            }
            
            /* Hide end date input when start calendar is open */
            .side-panel-filter-group:has(#start-date-picker-picker.SingleDatePicker_picker) #end-date-picker {
                display: none !important;
            }
            
            /* Hide entire end date section */
            .side-panel-filter-group:has(.SingleDatePicker_picker__openDown[data-picker-for="start-date-picker"]) #end-date-wrapper {
                display: none !important;
            }
            
            /* Ensure calendar doesn't overflow sidebar */
            .side-panel-filter-group {
                overflow: visible !important;
                position: relative !important;
            }
            
            /* Ensure date picker container is above other filter groups */
            .side-panel-filter-group:has(.professional-date-picker-container) {
                z-index: 1000 !important;
            }
            
            /* Fix calendar position to align with input field */
            .SingleDatePicker_picker {
                position: fixed !important;
                left: 0 !important;
                bottom: auto !important;
                top: auto !important;
                margin-bottom: 50px !important;
                z-index: 999999 !important;
                max-height: 500px !important;
                overflow-y: auto !important;
            }
            
            /* Ensure calendar is positioned correctly relative to its trigger */
            .SingleDatePicker_picker__openDown {
                position: fixed !important;
                z-index: 999999 !important;
                transform: none !important;
                left: 0 !important;
                bottom: auto !important;
                top: auto !important;
            }
            
            /* Open calendar above the input */
            .SingleDatePicker_picker__openUp {
                position: fixed !important;
                z-index: 999999 !important;
                bottom: auto !important;
                top: auto !important;
            }
            
            /* Prevent calendar from affecting layout */
            .SingleDatePicker_picker,
            .DateRangePicker_picker {
                box-sizing: border-box !important;
            }
            
            /* Make sure calendar wrapper doesn't shift */
            .DatePicker__input-container > div {
                left: 0 !important;
                transform: none !important;
            }
            
            .Calendar {
                border-radius: 20px !important;
                overflow: visible !important;
                width: 100% !important;
            }
            
            .Calendar__header {
                background: linear-gradient(135deg, #FF6B35 0%, #F7931E 50%, #FF8C42 100%) !important;
                padding: 16px 20px !important;
                border-radius: 12px 12px 0 0 !important;
                color: white !important;
                font-weight: 700 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: space-between !important;
            }
            
            .Calendar__header button {
                background: rgba(255, 255, 255, 0.2) !important;
                border: none !important;
                color: white !important;
                border-radius: 50% !important;
                width: 32px !important;
                height: 32px !important;
                cursor: pointer !important;
                transition: all 0.3s ease !important;
            }
            
            .Calendar__header button:hover {
                background: rgba(255, 255, 255, 0.3) !important;
                transform: scale(1.1) !important;
            }
            
            .Calendar__monthSelector, .Calendar__yearSelector {
                background: white !important;
                border: 2px solid rgba(255, 107, 53, 0.3) !important;
                border-radius: 12px !important;
                padding: 8px 12px !important;
            }
            
            /* Calendar body styling */
            .Calendar__monthGrid {
                padding: 16px !important;
            }
            
            .Calendar__weekDays {
                display: grid !important;
                grid-template-columns: repeat(7, 1fr) !important;
                gap: 4px !important;
                margin-bottom: 8px !important;
            }
            
            .Calendar__weekDay {
                text-align: center !important;
                font-weight: 700 !important;
                color: #FF6B35 !important;
                font-size: 0.85rem !important;
                padding: 8px !important;
            }
            
            .Calendar__month {
                display: grid !important;
                grid-template-columns: repeat(7, 1fr) !important;
                gap: 4px !important;
            }
            
            .Calendar__day {
                border-radius: 8px !important;
                padding: 10px !important;
                text-align: center !important;
                cursor: pointer !important;
                transition: all 0.2s ease !important;
                font-weight: 600 !important;
                color: #2C3E50 !important;
                min-height: 40px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            
            .Calendar__day:hover {
                background: rgba(255, 107, 53, 0.1) !important;
                transform: scale(1.05) !important;
            }
            
            .Calendar__day--selected {
                background: linear-gradient(135deg, #FF6B35, #F7931E) !important;
                color: white !important;
                box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4) !important;
                font-weight: 800 !important;
                border: 2px solid rgba(255, 255, 255, 0.8) !important;
                transform: scale(1.05) !important;
            }
            
            /* Highlight today's date */
            .Calendar__day--today {
                background: rgba(255, 107, 53, 0.2) !important;
                border: 2px solid #FF6B35 !important;
                color: #FF6B35 !important;
                font-weight: 700 !important;
            }
            
            .Calendar__day--outside-month {
                color: #CCCCCC !important;
                opacity: 0.5 !important;
            }
            
            /* Preset Button Styling */
            .preset-btn {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.15), rgba(247, 147, 30, 0.15));
                border: 2px solid rgba(255, 107, 53, 0.4);
                border-radius: 10px;
                color: #FF6B35;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                outline: none;
                flex: 1;
                min-width: calc(50% - 4px);
                box-shadow: 0 2px 6px rgba(255, 107, 53, 0.1);
            }
            
            .preset-btn:hover {
                background: linear-gradient(135deg, #FF6B35, #F7931E);
                color: white;
                border-color: #FF6B35;
                transform: translateY(-3px) scale(1.02);
                box-shadow: 0 6px 16px rgba(255, 107, 53, 0.35);
            }
            
            .preset-btn:active {
                transform: translateY(-1px) scale(0.98);
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3);
            }
            
            /* Range Slider Styling - Orange Theme */
            .month-range-slider .rc-slider {
                height: 60px;
                padding: 12px 0;
            }
            
            .month-range-slider .rc-slider-track {
                background: linear-gradient(90deg, #FF6B35, #F7931E) !important;
                height: 10px;
                border-radius: 5px;
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3);
            }
            
            .month-range-slider .rc-slider-handle {
                border-color: #FFFFFF !important;
                background: linear-gradient(135deg, #FF6B35, #F7931E) !important;
                width: 28px;
                height: 28px;
                margin-top: -9px;
                box-shadow: 0 4px 16px rgba(255, 107, 53, 0.5), inset 0 2px 4px rgba(255, 255, 255, 0.3) !important;
                border-width: 3px !important;
            }
            
            .month-range-slider .rc-slider-handle:hover {
                border-color: #FFFFFF !important;
                box-shadow: 0 6px 20px rgba(255, 107, 53, 0.6), inset 0 2px 4px rgba(255, 255, 255, 0.4) !important;
                transform: scale(1.15);
            }
            
            .month-range-slider .rc-slider-handle:active {
                box-shadow: 0 8px 24px rgba(255, 107, 53, 0.7), inset 0 2px 4px rgba(255, 255, 255, 0.5) !important;
                transform: scale(1.08);
            }
            
            .month-range-slider .rc-slider-handle:focus {
                border-color: #FFFFFF !important;
                box-shadow: 0 0 0 8px rgba(255, 107, 53, 0.3) !important;
            }
            
            .month-range-slider .rc-slider-rail {
                background-color: rgba(255, 107, 53, 0.15) !important;
                height: 10px;
                border-radius: 5px;
            }
            
            .month-range-slider .rc-slider-dot {
                border-color: rgba(255, 107, 53, 0.5) !important;
                width: 12px;
                height: 12px;
                margin-top: -1px;
                background-color: rgba(255, 107, 53, 0.2);
            }
            
            .month-range-slider .rc-slider-dot-active {
                border-color: #FF6B35 !important;
                background-color: #FF6B35 !important;
                box-shadow: 0 2px 8px rgba(255, 107, 53, 0.4);
            }
            
            .month-range-slider .rc-slider-mark {
                top: -5px;
            }
            
            .month-range-slider .rc-slider-mark-text {
                color: #FF6B35 !important;
                font-weight: 800 !important;
                font-size: 0.75rem !important;
                letter-spacing: 0.5px;
                text-shadow: 0 1px 2px rgba(255, 107, 53, 0.2);
                white-space: nowrap !important;
                margin-top: 8px !important;
            }
            
            .month-range-slider .rc-slider-tooltip-inner {
                background: linear-gradient(135deg, #FF6B35, #F7931E) !important;
                border-radius: 10px;
                font-weight: 800;
                font-size: 0.9rem;
                padding: 8px 16px;
                box-shadow: 0 6px 20px rgba(255, 107, 53, 0.4);
                border: 2px solid rgba(255, 255, 255, 0.3);
                color: white;
                letter-spacing: 0.5px;
            }
            
            .month-range-slider .rc-slider-tooltip-arrow {
                border-top-color: #FF6B35 !important;
            }
            
            /* Dropdown Styling - Orange Theme */
            .Select-control {
                border: 2px solid rgba(255, 107, 53, 0.25) !important;
                border-radius: 12px !important;
                background: linear-gradient(135deg, #ffffff 0%, #fff8f0 100%) !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                box-shadow: 0 3px 10px rgba(255, 107, 53, 0.12) !important;
                min-height: 48px !important;
            }
            
            .Select-control:hover {
                border-color: rgba(255, 107, 53, 0.5) !important;
                box-shadow: 0 5px 16px rgba(255, 107, 53, 0.25) !important;
                transform: translateY(-2px);
            }
            
            .is-focused .Select-control {
                border-color: #FF6B35 !important;
                box-shadow: 0 0 0 5px rgba(255, 107, 53, 0.2), 0 8px 20px rgba(255, 107, 53, 0.25) !important;
            }
            
            .Select-menu-outer {
                border: 2px solid rgba(255, 107, 53, 0.25) !important;
                border-radius: 14px !important;
                box-shadow: 0 10px 30px rgba(255, 107, 53, 0.25) !important;
                background: white !important;
                overflow: hidden;
            }
            
            .Select-option {
                color: #2C3E50 !important;
                font-weight: 700 !important;
                transition: all 0.2s ease !important;
                padding: 12px 16px !important;
            }
            
            .Select-option:hover {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.1), rgba(247, 147, 30, 0.1)) !important;
                color: #FF6B35 !important;
                transform: translateX(4px);
            }
            
            .Select-option.is-selected {
                background: linear-gradient(135deg, #FF6B35, #F7931E) !important;
                color: white !important;
                font-weight: 700 !important;
            }
            
            .Select-value-label {
                color: #2C3E50 !important;
                font-weight: 700 !important;
            }
            
            .Select-arrow-zone {
                color: #FF6B35 !important;
            }
            
            /* Professional Loading States */
            .loading-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 248, 240, 0.8) 100%);
                backdrop-filter: blur(10px);
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 28px;
                z-index: 10;
            }
            
            .loading-spinner {
                width: 40px;
                height: 40px;
                border: 3px solid rgba(255, 165, 0, 0.2);
                border-top: 3px solid #FF8C00;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Enhanced Spacing */
            .mb-5 {
                margin-bottom: 3rem !important;
            }
            
            .mb-4 {
                margin-bottom: 2.5rem !important;
            }
            
            .mb-3 {
                margin-bottom: 2rem !important;
            }
            
            /* Professional Typography */
            h1, h2, h3, h4, h5, h6 {
                font-weight: 600;
                letter-spacing: -0.02em;
                line-height: 1.3;
            }
            
            .metric-title {
                font-weight: 500;
                font-size: 0.9rem;
                letter-spacing: 0.02em;
                text-transform: uppercase;
                opacity: 0.8;
            }
            
            .metric-value {
                font-weight: 700;
                font-size: 2.2rem;
                letter-spacing: -0.03em;
                line-height: 1.1;
            }
            
            /* Enhanced Chart Styling */
            .js-plotly-plot {
                border-radius: 0 0 28px 28px;
                overflow: hidden;
            }
            
            /* Professional Button Styling */
            .btn-primary {
                background: linear-gradient(135deg, #FF8C00 0%, #FFA500 100%);
                border: none;
                border-radius: 12px;
                padding: 12px 24px;
                font-weight: 600;
                letter-spacing: 0.02em;
                box-shadow: 0 4px 15px rgba(255, 140, 0, 0.3);
                transition: all 0.3s ease;
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(255, 140, 0, 0.4);
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        <script>
            // Monitor and hide end date when start calendar is open
            setInterval(function() {
                var endWrapper = document.getElementById('end-date-wrapper');
                var startPicker = document.querySelector('#start-date-picker');
                
                if (endWrapper && startPicker) {
                    // Check if calendar picker exists (calendar is open)
                    var calendarOpen = startPicker.querySelector('.SingleDatePicker_picker');
                    if (calendarOpen) {
                        endWrapper.style.display = 'none';
                    } else {
                        endWrapper.style.display = 'block';
                    }
                }
            }, 200);
        </script>
    </body>
</html>
'''

# Create the layout
app.layout = html.Div([
    # Auto-refresh interval component
    interval_component,
    # Toggle Button
    html.Button(
        html.I(className="fas fa-bars"),
        id='panel-toggle',
        n_clicks=0,
        className="panel-toggle-btn"
    ),
    
    # Side Panel
    html.Div(id='side-panel', className="side-panel", children=[
        html.Div([
            html.I(className="fas fa-sliders-h", style={'marginRight': '12px', 'fontSize': '1.3rem'}),
            html.Span("Filters & Analysis", style={'letterSpacing': '1px'})
        ], className="side-panel-header"),
        html.Div(className="side-panel-content", children=[
            # Date Range Filter - Advanced Calendar with Presets
            html.Div([
                html.Div([
                    html.I(className="fas fa-calendar-alt"),
                    html.Label("Analysis Period")
                ], className="side-panel-icon-label"),
                
                # Year Range Selector
                html.Div([
                    html.P("Year Range", style={'fontSize': '0.75rem', 'fontWeight': '600', 'color': '#6C757D', 'marginBottom': '10px', 'textTransform': 'uppercase', 'letterSpacing': '0.5px'}),
                    html.Div([
                        html.Div([
                            html.P("From Year", style={'fontSize': '0.7rem', 'fontWeight': '600', 'color': '#FF6B35', 'marginBottom': '6px'}),
                            dcc.Dropdown(
                                id='from-year-dropdown',
                                options=[{'label': str(year), 'value': year} for year in range(solar_flare_df['observation_date'].dt.year.min(), solar_flare_df['observation_date'].dt.year.max() + 1)],
                                value=solar_flare_df['observation_date'].dt.year.min(),
                                clearable=False,
                                style={'backgroundColor': 'white', 'borderRadius': '8px'}
                            )
                        ], style={'flex': '1', 'marginRight': '8px'}),
                        html.Div([
                            html.P("To Year", style={'fontSize': '0.7rem', 'fontWeight': '600', 'color': '#FF6B35', 'marginBottom': '6px'}),
                            dcc.Dropdown(
                                id='to-year-dropdown',
                                options=[{'label': str(year), 'value': year} for year in range(solar_flare_df['observation_date'].dt.year.min(), solar_flare_df['observation_date'].dt.year.max() + 1)],
                                value=solar_flare_df['observation_date'].dt.year.max(),
                                clearable=False,
                                style={'backgroundColor': 'white', 'borderRadius': '8px'}
                            )
                        ], style={'flex': '1', 'marginLeft': '8px'})
                    ], style={'display': 'flex', 'gap': '8px', 'marginBottom': '12px'})
                ], style={'marginBottom': '20px'}),
                
                # Start Month Selector
                html.Div([
                    html.P("Start Month", style={'fontSize': '0.75rem', 'fontWeight': '600', 'color': '#6C757D', 'marginBottom': '8px', 'textTransform': 'uppercase', 'letterSpacing': '0.5px'}),
                    dcc.Slider(
                        id='start-month-slider',
                        min=1,
                        max=12,
                        value=1,
                        step=1,
                        marks=None,
                        tooltip={"placement": "bottom", "always_visible": True},
                        className="month-range-slider"
                    )
                ], style={'marginBottom': '16px'}),
                
                # End Month Selector
                html.Div([
                    html.P("End Month", style={'fontSize': '0.75rem', 'fontWeight': '600', 'color': '#6C757D', 'marginBottom': '8px', 'textTransform': 'uppercase', 'letterSpacing': '0.5px'}),
                    dcc.Slider(
                        id='end-month-slider',
                        min=1,
                        max=12,
                        value=12,
                        step=1,
                        marks=None,
                        tooltip={"placement": "bottom", "always_visible": True},
                        className="month-range-slider"
                    )
                ], style={'marginBottom': '16px'}),
                
                # Start Date Calendar
                html.Div([
                    html.P("Start Date", style={'fontSize': '0.85rem', 'fontWeight': '600', 'color': '#FF6B35', 'marginBottom': '8px'}),
                    html.Div([
                        dcc.DatePickerSingle(
                            id='start-date-picker',
                            date=solar_flare_df['observation_date'].min(),
                            display_format='MMM DD, YYYY',
                            style={'width': '100%'},
                            className="professional-date-picker",
                            show_outside_days=True,
                            month_format='MMMM YYYY',
                            day_size=40,
                            number_of_months_shown=1,
                            with_portal=False,
                            with_full_screen_portal=False,
                            calendar_orientation='vertical'
                        )
                    ], className="professional-date-picker-container")
                ], style={'marginBottom': '16px'}),
                
                # End Date Calendar
                html.Div([
                    html.P("End Date", style={'fontSize': '0.85rem', 'fontWeight': '600', 'color': '#FF6B35', 'marginBottom': '8px'}),
                    html.Div([
                        dcc.DatePickerSingle(
                            id='end-date-picker',
                            date=solar_flare_df['observation_date'].max(),
                            display_format='MMM DD, YYYY',
                            style={'width': '100%'},
                            className="professional-date-picker",
                            show_outside_days=True,
                            month_format='MMMM YYYY',
                            day_size=40,
                            number_of_months_shown=1,
                            with_portal=False,
                            with_full_screen_portal=False,
                            calendar_orientation='vertical'
                        )
                    ], className="professional-date-picker-container")
                ], id='end-date-wrapper')
            ], className="side-panel-filter-group"),
            
            # Flare Class Filter
            html.Div([
                html.Div([
                    html.I(className="fas fa-bolt"),
                    html.Label("Flare Classes")
                ], className="side-panel-icon-label"),
                dcc.Checklist(
                    id='flare-class-filter',
                    options=[
                        {'label': ' X-Class', 'value': 'X'},
                        {'label': ' M-Class', 'value': 'M'},
                        {'label': ' C-Class', 'value': 'C'}
                    ],
                    value=['X', 'M', 'C'],
                    style={'display': 'flex', 'flexDirection': 'column', 'gap': '8px'}
                )
            ], className="side-panel-filter-group"),
            
            # Solar Cycle Phase Filter
            html.Div([
                html.Div([
                    html.I(className="fas fa-sync-alt"),
                    html.Label("Solar Cycle Phases")
                ], className="side-panel-icon-label"),
                dcc.Checklist(
                    id='cycle-phase-filter',
                    options=[
                        {'label': ' Rising', 'value': 'Rising'},
                        {'label': ' Peak', 'value': 'Peak'},
                        {'label': ' Declining', 'value': 'Declining'},
                        {'label': ' Minimum', 'value': 'Minimum'}
                    ],
                    value=['Rising', 'Peak', 'Declining', 'Minimum'],
                    style={'display': 'flex', 'flexDirection': 'column', 'gap': '8px'}
                )
            ], className="side-panel-filter-group"),
            
            # Magnetic Complexity Filter
            html.Div([
                html.Div([
                    html.I(className="fas fa-magnet"),
                    html.Label("Magnetic Complexity")
                ], className="side-panel-icon-label"),
                dcc.Checklist(
                    id='magnetic-complexity-filter',
                    options=[
                        {'label': ' Alpha', 'value': 'Alpha'},
                        {'label': ' Beta', 'value': 'Beta'},
                        {'label': ' Gamma', 'value': 'Gamma'},
                        {'label': ' Delta', 'value': 'Delta'}
                    ],
                    value=['Alpha', 'Beta', 'Gamma', 'Delta'],
                    style={'display': 'flex', 'flexDirection': 'column', 'gap': '8px'}
                )
            ], className="side-panel-filter-group"),
            
            # Sunspot Count Filter
            html.Div([
                html.Div([
                    html.I(className="fas fa-circle"),
                    html.Label("Sunspot Count")
                ], className="side-panel-icon-label"),
                dcc.RangeSlider(
                    id='sunspot-count-slider',
                    min=float(solar_flare_df['sunspot_count'].min()),
                    max=float(solar_flare_df['sunspot_count'].max()),
                    value=[float(solar_flare_df['sunspot_count'].min()), float(solar_flare_df['sunspot_count'].max())],
                    marks={
                        int(solar_flare_df['sunspot_count'].min()): {'label': f"{int(solar_flare_df['sunspot_count'].min())}", 'style': {'color': '#FF6B35', 'fontSize': '0.7rem'}},
                        int(solar_flare_df['sunspot_count'].max()): {'label': f"{int(solar_flare_df['sunspot_count'].max())}", 'style': {'color': '#FF6B35', 'fontSize': '0.7rem'}}
                    },
                    tooltip={"placement": "bottom", "always_visible": True},
                    className="month-range-slider"
                )
            ], className="side-panel-filter-group"),
            
            # Flare Occurred Filter
            html.Div([
                html.Div([
                    html.I(className="fas fa-fire"),
                    html.Label("Flare Activity")
                ], className="side-panel-icon-label"),
                dcc.Checklist(
                    id='flare-occurred-filter',
                    options=[
                        {'label': ' Flares Occurred', 'value': 1},
                        {'label': ' No Flares', 'value': 0}
                    ],
                    value=[0, 1],
                    style={'display': 'flex', 'flexDirection': 'column', 'gap': '8px'}
                )
            ], className="side-panel-filter-group"),
            
            # Active Filters Summary
            html.Div([
                html.Div([
                    html.I(className="fas fa-info-circle"),
                    html.Label("Active Filters")
                ], className="side-panel-icon-label"),
                html.Div(id='filter-summary', className="summary-card")
            ], className="side-panel-filter-group")
        ]),
    ]),
    
    # Main Content
    html.Div(id='main-content', className="main-content-wrapper", children=[
        dbc.Container([
            # Header Section
            dbc.Row([
                dbc.Col([
                    html.Div([
                         html.H1("PROJECT HYPERION", 
                                className="text-center mb-2 project-title"),
                         html.P("Sunspot and Flare Monitoring Hub", 
                                className="text-center mb-4 project-subtitle")
                    ])
                ])
            ], className="mb-5"),
            
            # Key Performance Indicators
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Div([
                                    html.I(className="fas fa-bolt icon-gradient")
                                ]),
                                html.Div("Total Flares (Count)", className="title-gradient"),
                                html.Div(id="total-flares", className="value-gradient")
                            ], className="text-center")
                        ])
                    ], className="metric-card")
                ], width=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Div([
                                    html.I(className="fas fa-sun icon-gradient")
                                ]),
                                html.Div("Average Sunspots (Count)", className="title-gradient"),
                                html.Div(id="avg-sunspots", className="value-gradient")
                            ], className="text-center")
                        ])
                    ], className="metric-card")
                ], width=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Div([
                                    html.I(className="fas fa-chart-line icon-gradient")
                                ]),
                                html.Div("Max Flare Index (Scale)", className="title-gradient"),
                                html.Div(id="max-flare-index", className="value-gradient")
                            ], className="text-center")
                        ])
                    ], className="metric-card")
                ], width=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Div([
                                    html.I(className="fas fa-globe icon-gradient")
                                ]),
                                html.Div("Active Regions (Count)", className="title-gradient"),
                                html.Div(id="active-regions", className="value-gradient")
                            ], className="text-center")
                        ])
                    ], className="metric-card")
                ], width=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Div([
                                    html.I(className="fas fa-star icon-gradient")
                                ]),
                                html.Div("M-Class Flares (Count)", className="title-gradient"),
                                html.Div(id="x-class-flares", className="value-gradient")
                            ], className="text-center")
                        ])
                    ], className="metric-card")
                ], width=2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Div([
                                    html.I(className="fas fa-sun icon-gradient")
                                ]),
                                html.Div("Solar Flux (SFU)", className="title-gradient"),
                                html.Div(id="solar-wind-speed", className="value-gradient")
                            ], className="text-center")
                        ])
                    ], className="metric-card")
                ], width=2)
            ], className="mb-5"),
            
            
            # Beautiful Orange-Themed Layout - 2x3 Grid Format
            # Row 1: 3 Charts - Flare Distribution, Solar Cycle Phases, Geomagnetic Index
            dbc.Row([
                # Chart 1: Flare Class Distribution (Orange Theme)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.Span("Flare Class Distribution", style={'color': 'white'})
                            ])
                        ], className="chart-header"),
                        dbc.CardBody([
                            dcc.Graph(id='flare-class-distribution')
                        ])
                    ], className="ultimate-card")
                ], width=4),
                
                # Chart 2: Solar Cycle Phases (Orange Theme)
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                            html.Span("Solar Cycle Phases", style={'color': 'white'})
                            ])
                        ], className="chart-header"),
                        dbc.CardBody([
                            dcc.Graph(id='magnetic-donut-chart')
                        ])
                    ], className="ultimate-card")
                ], width=4),
                
                # Chart 3: Geomagnetic Index Analysis
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                            html.Span("Geomagnetic Index Analysis", style={'color': 'white'})
                            ])
                        ], className="chart-header"),
                        dbc.CardBody([
                            dcc.Graph(id='solar-wind-chart')
                        ])
                    ], className="ultimate-card")
                ], width=4)
            ], className="mb-4"),
            
            # Row 2: 3 Charts - Temperature Distribution, Solar Activity Trends, Solar Flux Distribution
            dbc.Row([
                # Chart 4: Temperature Variation Distribution
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                            html.Span("Temperature Variation Over Time", style={'color': 'white'})
                            ])
                        ], className="chart-header"),
                        dbc.CardBody([
                            dcc.Graph(id='flare-energy-chart')
                        ])
                    ], className="ultimate-card")
                ], width=4),
                
                # Chart 5: Solar Activity Trends
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                            html.Span("Solar Activity Categories", style={'color': 'white'})
                            ])
                        ], className="chart-header"),
                        dbc.CardBody([
                            dcc.Graph(id='solar-activity-area')
                        ])
                    ], className="ultimate-card")
                ], width=4),
                
                # Chart 6: Solar Flux Distribution
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                            html.Span("Solar Flux Distribution", style={'color': 'white'})
                            ])
                        ], className="chart-header"),
                        dbc.CardBody([
                            dcc.Graph(id='flare-intensity-bar')
                        ])
                    ], className="ultimate-card")
                ], width=4)
            ], className="mb-4"),
            
       # Row 3: Two Additional Charts (1x2 Layout)
            dbc.Row([
           # Chart 8: Solar Wind Speed Analysis
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                           html.Span("Solar Wind Speed Analysis", style={'color': 'white'})
                            ])
                        ], className="chart-header"),
                        dbc.CardBody([
                       dcc.Graph(id='solar-wind-speed-chart')
                        ])
                    ], className="ultimate-card")
                ], width=6),
                
           # Chart 9: Solar Irradiance Distribution
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                           html.Span("Solar Flux Levels", style={'color': 'white'})
                            ])
                        ], className="chart-header"),
                        dbc.CardBody([
                       dcc.Graph(id='solar-irradiance-chart')
                        ])
                    ], className="ultimate-card")
                ], width=6)
            ], className="mb-4"),
            
       # Row 4: Large Sunspot Activity Timeline (Full Width) - Moved to Bottom
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                           html.Span("Sunspot Activity and Solar Flux Timeline", style={'color': 'white'})
                            ])
                        ], className="chart-header"),
                        dbc.CardBody([
                       dcc.Graph(id='sunspot-timeline')
                        ])
                    ], className="ultimate-card")
                ], width=12)
       ], className="mb-4"),
            
    
        ], fluid=True, style={'backgroundColor': 'transparent', 'minHeight': '100vh', 'padding': '2rem 0'})
    ])
])

# Callback for toggling sidebar
@app.callback(
    [Output('side-panel', 'className'),
     Output('main-content', 'className'),
     Output('panel-toggle', 'className')],
    [Input('panel-toggle', 'n_clicks')]
)
def toggle_sidebar(n_clicks):
    if n_clicks % 2 == 0:
        # Panel is open
        return 'side-panel', 'main-content-wrapper', 'panel-toggle-btn'
    else:
        # Panel is closed
        return 'side-panel side-panel-collapsed', 'main-content-wrapper main-content-wrapper-expanded', 'panel-toggle-btn panel-toggle-btn-collapsed'

# Callback for year and month selectors
@app.callback(
    [Output('start-date-picker', 'date', allow_duplicate=True),
     Output('end-date-picker', 'date', allow_duplicate=True)],
    [Input('from-year-dropdown', 'value'),
     Input('to-year-dropdown', 'value'),
     Input('start-month-slider', 'value'),
     Input('end-month-slider', 'value')],
    prevent_initial_call=True
)
def update_dates_from_year_month(from_year, to_year, start_month, end_month):
    # Handle None values
    if not from_year or not to_year or start_month is None or end_month is None:
        raise PreventUpdate
    
    start_month = int(start_month)
    end_month = int(end_month)
    
    # Start date: first day of start month in from_year
    start_date = pd.Timestamp(f'{from_year}-{start_month:02d}-01')
    
    # End date: last day of end month in to_year
    if end_month == 12:
        end_date = pd.Timestamp(f'{to_year}-12-31')
    else:
        end_date = pd.Timestamp(f'{to_year}-{end_month+1:02d}-01') - pd.Timedelta(days=1)
    
    # Clamp to actual data range
    start_date = max(start_date, solar_flare_df['observation_date'].min())
    end_date = min(end_date, solar_flare_df['observation_date'].max())
    
    # Convert to string format for DatePickerSingle
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

# Callback for filter summary
@app.callback(
    Output('filter-summary', 'children'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('cycle-phase-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_filter_summary(start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    summary_items = []
    
    if start_date and end_date:
        summary_items.append(html.Div([
            html.Strong("Period: "),
            f"{start_date} to {end_date}"
        ], className="summary-item"))
    
    if flare_classes:
        summary_items.append(html.Div([
            html.Strong("Flare Classes: "),
            ', '.join(flare_classes)
        ], className="summary-item"))
    
    if cycle_phases:
        summary_items.append(html.Div([
            html.Strong("Cycle Phases: "),
            ', '.join(cycle_phases)
        ], className="summary-item"))
    
    if magnetic_types and len(magnetic_types) < 4:
        summary_items.append(html.Div([
            html.Strong("Magnetic: "),
            ', '.join(magnetic_types)
        ], className="summary-item"))
    
    if sunspot_range:
        summary_items.append(html.Div([
            html.Strong("Sunspot Count: "),
            f"{sunspot_range[0]:.0f} - {sunspot_range[1]:.0f}"
        ], className="summary-item"))
    
    if flare_occurred and len(flare_occurred) == 1:
        summary_items.append(html.Div([
            html.Strong("Flare Status: "),
            'Occurred' if flare_occurred[0] == 1 else 'No Flares'
        ], className="summary-item"))
    
    if summary_items:
        return html.Div(summary_items)
    else:
        return html.P("No filters applied", style={'color': '#6C757D', 'fontStyle': 'italic', 'margin': '0'})

# Original metrics callback removed to prevent conflicts with enhanced version


# Callback for sunspot timeline
@app.callback(
    Output('sunspot-timeline', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('cycle-phase-filter', 'value')]
)
def update_sunspot_timeline(start_date, end_date, cycle_phases):
    try:
        # Handle None dates
        if start_date is None:
            start_date = sunspot_df['date'].min()
        if end_date is None:
            end_date = sunspot_df['date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None cycle_phases
        if cycle_phases is None or len(cycle_phases) == 0:
            cycle_phases = ['Rising', 'Peak', 'Declining', 'Minimum']
    except Exception as e:
        print(f"ERROR in update_sunspot_timeline (date handling): {str(e)}")
        raise PreventUpdate
    
    try:
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date) &
            (sunspot_df['solar_cycle_phase'].isin(cycle_phases))
        ].copy()
        
        if len(sunspot_filtered) == 0:
            return go.Figure().add_annotation(text="No data available for selected filters", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Daily aggregation
        period_data = sunspot_filtered.groupby('date').agg({
            'total_sunspots': 'mean',
            'solar_flux': 'mean'
        }).reset_index()
        
        fig = go.Figure()
        
        # Sunspots - Sunrise orange solid line with area fill and thick markers
        fig.add_trace(go.Scatter(
            x=period_data['date'],
            y=period_data['total_sunspots'],
            mode='lines+markers',
            name='Total Sunspots',
            line=dict(color='#FF8C00', width=6, shape='spline'),
            marker=dict(
                size=12, 
                color='#FF8C00', 
                line=dict(width=4, color='white'), 
                symbol='circle',
                opacity=0.9
            ),
            fill='tozeroy',
            fillcolor='rgba(255, 140, 0, 0.4)',
            hovertemplate='<b>Total Sunspots</b><br>Date: %{x}<br>Count: %{y}<br>Range: 0-299<extra></extra>',
            showlegend=True
        ))
        
        # Solar Flux - Gold thick dashed line with star markers
        fig.add_trace(go.Scatter(
            x=period_data['date'],
            y=period_data['solar_flux'],
            mode='lines+markers',
            name='Solar Flux',
            yaxis='y2',
            line=dict(
                color='#FFD700', 
                width=5, 
                shape='spline', 
                dash='dashdot'
            ),
            marker=dict(
                size=10, 
                color='#FFD700', 
                line=dict(width=3, color='white'), 
                symbol='star',
                opacity=0.8
            ),
            hovertemplate='<b>Solar Flux</b><br>Date: %{x}<br>Flux: %{y} SFU<br>Range: 60-250<extra></extra>',
            showlegend=True
        ))
        
        fig.update_layout(
            xaxis=dict(
                title=dict(text="Date", font=dict(size=16, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)', 
                showgrid=True,
                linecolor='rgba(255, 107, 53, 0.3)',
                tickfont=dict(size=14, color='#2C3E50', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Total Sunspots", font=dict(size=18, color='#FF8C00', family='Inter')),
                side="left", 
                color='#FF8C00', 
                gridcolor='rgba(255, 140, 0, 0.3)', 
                showgrid=True,
                linecolor='rgba(255, 140, 0, 0.8)',
                linewidth=3,
                tickfont=dict(size=15, color='#FF8C00', family='Inter')
            ),
            yaxis2=dict(
                title=dict(text="Solar Flux (SFU)", font=dict(size=18, color='#FFD700', family='Inter')),
                side="right", 
                overlaying="y", 
                color='#FFD700',
                gridcolor='rgba(255, 215, 0, 0.3)',
                linecolor='rgba(255, 215, 0, 0.8)',
                linewidth=3,
                tickfont=dict(size=15, color='#FFD700', family='Inter')
            ),
            hovermode='x unified',
            template='none',
            height=600,  # Increased height for larger chart
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="center", 
                x=0.5,
                bgcolor='rgba(255, 255, 255, 0.95)',
                bordercolor='rgba(255, 107, 53, 0.5)',
                borderwidth=3,
                font=dict(size=16, color='#2C3E50', family='Inter'),
                itemsizing='constant',
                itemwidth=40
            ),
            margin=dict(t=120, b=100, l=100, r=100),  # Increased margins for larger chart
            hoverlabel=dict(
                bgcolor='rgba(255, 255, 255, 0.95)', 
                bordercolor='#FF6B35', 
                font=dict(size=14, color='#2C3E50', family='Inter')
            ),
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_sunspot_timeline: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for Solar Wind Speed Analysis
@app.callback(
    Output('solar-wind-speed-chart', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('cycle-phase-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_solar_wind_speed_chart(start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Apply filters to sunspot data
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date)
        ].copy()
        
        if len(sunspot_filtered) == 0:
            return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create solar wind speed data
        wind_data = sunspot_filtered.groupby(sunspot_filtered['date'].dt.to_period('M')).agg({
            'avg_solar_wind_speed': 'mean',
            'total_sunspots': 'mean'
        }).reset_index()
        
        wind_data['date'] = wind_data['date'].dt.to_timestamp()
        
        # Beautiful Orange Theme for Solar Wind Speed - Area Chart
        fig = go.Figure(data=[go.Scatter(
            x=wind_data['date'],
            y=wind_data['avg_solar_wind_speed'],
                mode='lines+markers',
            name='Solar Wind Speed',
            line=dict(color='#FF6B35', width=4, shape='spline'),
            marker=dict(size=8, color='#FF8C42', line=dict(width=2, color='white')),
                fill='tozeroy',
            fillcolor='rgba(255, 107, 53, 0.3)',
            hovertemplate='<b>Date:</b> %{x}<br><b>Wind Speed:</b> %{y} km/s<extra></extra>'
        )])
        
        fig.update_layout(
            xaxis=dict(
                title=dict(text="Date", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                gridcolor='rgba(255, 107, 53, 0.2)',
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Wind Speed (km/s)", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                gridcolor='rgba(255, 107, 53, 0.2)',
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=60, l=60, r=60)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_solar_wind_speed_chart: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for Solar Irradiance Distribution
@app.callback(
    Output('solar-irradiance-chart', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('cycle-phase-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_solar_irradiance_chart(start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Apply filters to sunspot data
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date)
        ].copy()
        
        if len(sunspot_filtered) == 0:
            return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create solar irradiance scatter plot data
        irradiance_data = sunspot_filtered.groupby(sunspot_filtered['date'].dt.to_period('M')).agg({
            'solar_flux': 'mean',
            'total_sunspots': 'mean',
            'geomagnetic_index': 'mean'
        }).reset_index()
        
        irradiance_data['date'] = irradiance_data['date'].dt.to_timestamp()
        
        # Beautiful Orange Theme for Solar Flux Levels - Polar Chart
        # Create flux level categories
        irradiance_data['flux_level'] = pd.cut(
            irradiance_data['solar_flux'], 
            bins=[0, 80, 120, 160, 200, float('inf')], 
            labels=['Very Low', 'Low', 'Medium', 'High', 'Very High']
        )
        
        # Count flux levels
        flux_counts = irradiance_data['flux_level'].value_counts()
        
        # Create polar chart data
        categories = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
        values = [flux_counts.get(cat, 0) for cat in categories]
        
        # Beautiful Orange Theme for Flux Levels - Polar Chart
        fig = go.Figure(data=[go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Solar Flux Levels',
            line_color='#FF6B35',
            fillcolor='rgba(255, 107, 53, 0.3)',
            marker=dict(
                size=8,
                color='#FF6B35',
                line=dict(color='white', width=2)
            ),
            hovertemplate='<b>%{theta}</b><br>Count: %{r}<br><extra></extra>'
        )])
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(values) if max(values) > 0 else 1],
                    color='#FF6B35',
                    gridcolor='rgba(255, 107, 53, 0.3)',
                    tickfont=dict(size=12, color='#FF6B35', family='Inter')
                ),
                angularaxis=dict(
                    color='#FF6B35',
                    tickfont=dict(size=12, color='#FF6B35', family='Inter')
                )
            ),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=60, b=60, l=60, r=60)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_solar_irradiance_chart: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for flare class distribution
@app.callback(
    Output('flare-class-distribution', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_flare_class_distribution(start_date, end_date, flare_classes, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None filters
        if flare_classes is None or len(flare_classes) == 0:
            flare_classes = ['X', 'M', 'C']
        if magnetic_types is None or len(magnetic_types) == 0:
            magnetic_types = ['Alpha', 'Beta', 'Gamma', 'Delta']
        if sunspot_range is None or len(sunspot_range) < 2:
            sunspot_range = [float(solar_flare_df['sunspot_count'].min()), float(solar_flare_df['sunspot_count'].max())]
        if flare_occurred is None or len(flare_occurred) == 0:
            flare_occurred = [0, 1]
    except Exception as e:
        raise PreventUpdate
    
    try:
        # Apply comprehensive filtering for dynamic data
        flare_filtered = solar_flare_df[
            (solar_flare_df['observation_date'] >= start_date) & 
            (solar_flare_df['observation_date'] <= end_date)
        ].copy()
        
        # Apply magnetic complexity filter if column exists
        if 'magnetic_complexity' in flare_filtered.columns:
            flare_filtered = flare_filtered[flare_filtered['magnetic_complexity'].isin(magnetic_types)]
        
        # Apply sunspot count filter
        flare_filtered = flare_filtered[
            (flare_filtered['sunspot_count'] >= sunspot_range[0]) &
            (flare_filtered['sunspot_count'] <= sunspot_range[1])
        ]
        
        # Apply flare occurred filter
        flare_filtered = flare_filtered[flare_filtered['flare_occurred'].isin(flare_occurred)]
        
        # Calculate dynamic flare totals based on selected classes
        flare_totals = {}
        if 'X' in flare_classes:
            x_count = flare_filtered['x_class_flares'].sum()
            if x_count > 0:
                flare_totals['X-Class'] = x_count
        if 'M' in flare_classes:
            m_count = flare_filtered['m_class_flares'].sum()
            if m_count > 0:
                flare_totals['M-Class'] = m_count
        if 'C' in flare_classes:
            c_count = flare_filtered['c_class_flares'].sum()
            if c_count > 0:
                flare_totals['C-Class'] = c_count
        
        if not flare_totals:
            flare_totals = {'No Data': 0}
        
        # Sunrise Orange Theme for Flare Distribution
        color_map = {
            'X-Class': '#FF4500',  # Orange Red
            'M-Class': '#FF8C00',  # Dark Orange
            'C-Class': '#FFA500',  # Orange
            'B-Class': '#FFB347',  # Peach
            'A-Class': '#FFD700'   # Gold
        }
        colors_list = [color_map.get(label, '#FFB366') for label in flare_totals.keys()]
        
        # Create a more prominent donut chart with better visibility
        fig = go.Figure(data=[go.Pie(
            labels=list(flare_totals.keys()),
            values=list(flare_totals.values()),
            hole=0.4,  # Smaller hole for more visible data
            marker_colors=colors_list,
            textinfo='label+value+percent',
            textfont_size=16,
            textfont_color='white',
            textfont_family='Inter',
            hovertemplate='<b>%{label}</b><br>Flare Count: %{value:,}<br>Percentage: %{percent}<br><extra></extra>',
            marker_line=dict(color='white', width=3),
            rotation=0,  # Start from top
            pull=[0.15, 0.1, 0.05],  # More prominent pull for visual appeal
            textposition='inside',
            insidetextorientation='radial'
        )])
        
        # Add center annotation showing total flares
        total_flares = sum(flare_totals.values())
        
        fig.update_layout(
            template='none',
            height=450,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            showlegend=True,
            legend=dict(
                orientation="v", 
                yanchor="middle", 
                y=0.5, 
                xanchor="left", 
                x=1.02,
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='rgba(255, 107, 53, 0.5)',
                borderwidth=2,
                font=dict(size=14, color='#2C3E50', family='Inter')
            ),
            margin=dict(t=80, b=60, l=60, r=120),
            hoverlabel=dict(
                bgcolor='rgba(255, 255, 255, 0.95)', 
                bordercolor='#FF6B35', 
                font=dict(size=12, color='#2C3E50', family='Inter')
            ),
            annotations=[
                dict(
                    text=f"<b>Total Flares</b><br>{total_flares:,}",
                    x=0.5, y=0.5,
                    font_size=16,
                    font_color='#2C3E50',
                    font_family='Inter',
                    showarrow=False,
                    xref='paper',
                    yref='paper'
                )
            ]
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(text="Error loading data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for solar cycle phase
@app.callback(
    Output('solar-cycle-phase', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('cycle-phase-filter', 'value')]
)
def update_solar_cycle_phase(start_date, end_date, cycle_phases):
    try:
        # Handle None dates
        if start_date is None:
            start_date = sunspot_df['date'].min()
        if end_date is None:
            end_date = sunspot_df['date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None cycle_phases
        if cycle_phases is None or len(cycle_phases) == 0:
            cycle_phases = ['Rising', 'Peak', 'Declining', 'Minimum']
    except Exception as e:
        raise PreventUpdate
    
    try:
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date) &
            (sunspot_df['solar_cycle_phase'].isin(cycle_phases))
        ]
        
        phase_counts = sunspot_filtered['solar_cycle_phase'].value_counts()
        
        color_map = {'Rising': '#FF6B35', 'Peak': '#DC3545', 
                     'Declining': '#F7931E', 'Minimum': '#6C757D'}
        colors_list = [color_map.get(phase, '#6C757D') for phase in phase_counts.index]
        
        fig = go.Figure(data=[go.Bar(
            x=phase_counts.index,
            y=phase_counts.values,
            marker_color=colors_list,
            marker_line=dict(color='white', width=3),
            text=phase_counts.values,
            textposition='auto',
            textfont=dict(color='white', size=16, family='Inter')
        )])
        
        fig.update_layout(
            title=dict(text="Solar Cycle Phase Distribution", 
                      font=dict(size=22, color='#2C3E50', family='Inter')),
            xaxis=dict(
                title=dict(text="Phase", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)', 
                showgrid=True,
                linecolor='rgba(255, 107, 53, 0.3)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Count", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)', 
                showgrid=True,
                linecolor='rgba(255, 107, 53, 0.3)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            template='none',
            height=450,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=80, l=80, r=80),
            hoverlabel=dict(
                bgcolor='rgba(255, 255, 255, 0.95)', 
                bordercolor='#FF6B35', 
                font=dict(size=12, color='#2C3E50', family='Inter')
            ),
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(text="Error loading data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for magnetic complexity
@app.callback(
    Output('magnetic-complexity', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date')]
)
def update_magnetic_complexity(start_date, end_date):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except Exception as e:
        raise PreventUpdate
    
    try:
        flare_filtered = solar_flare_df[
            (solar_flare_df['observation_date'] >= start_date) & 
            (solar_flare_df['observation_date'] <= end_date)
        ]
        
        complexity_counts = flare_filtered['magnetic_complexity'].value_counts()
        
        color_map = {'Alpha': '#FF6B35', 'Beta': '#F7931E', 
                     'Gamma': '#DC3545', 'Delta': '#6C757D'}
        colors_list = [color_map.get(complexity, '#6C757D') for complexity in complexity_counts.index]
        
        fig = go.Figure(data=[go.Bar(
            x=complexity_counts.index,
            y=complexity_counts.values,
            marker_color=colors_list,
            marker_line=dict(color='white', width=3),
            text=complexity_counts.values,
            textposition='auto',
            textfont=dict(color='white', size=16, family='Inter')
        )])
        
        fig.update_layout(
            title=dict(text="Magnetic Complexity Distribution", 
                      font=dict(size=22, color='#2C3E50', family='Inter')),
            xaxis=dict(
                title=dict(text="Complexity Type", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)', 
                showgrid=True,
                linecolor='rgba(255, 107, 53, 0.3)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Count", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)', 
                showgrid=True,
                linecolor='rgba(255, 107, 53, 0.3)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            template='none',
            height=450,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=80, l=80, r=80),
            hoverlabel=dict(
                bgcolor='rgba(255, 255, 255, 0.95)', 
                bordercolor='#FF6B35', 
                font=dict(size=12, color='#2C3E50', family='Inter')
            ),
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(text="Error loading data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for correlation matrix
@app.callback(
    Output('correlation-matrix', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date')]
)
def update_correlation_matrix(start_date, end_date):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except Exception as e:
        raise PreventUpdate
    
    try:
        flare_daily = solar_flare_df.groupby('observation_date').agg({
            'sunspot_count': 'mean',
            'flare_index': 'mean',
            'x_class_flares': 'sum',
            'm_class_flares': 'sum',
            'c_class_flares': 'sum'
        }).reset_index()
        
        combined = pd.merge(
            flare_daily, 
            sunspot_df[['date', 'total_sunspots', 'solar_flux']], 
            left_on='observation_date', 
            right_on='date', 
            how='inner'
        )
        
        combined_filtered = combined[
            (combined['observation_date'] >= start_date) & 
            (combined['observation_date'] <= end_date)
        ]
        
        numeric_cols = ['sunspot_count', 'flare_index', 'x_class_flares', 'm_class_flares', 
                       'c_class_flares', 'total_sunspots', 'solar_flux']
        
        corr_matrix = combined_filtered[numeric_cols].corr()
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmid=0,
            text=np.round(corr_matrix.values, 2),
            texttemplate="%{text}",
            textfont={"size": 12, "family": "Inter"},
            hovertemplate='<b>%{y} vs %{x}</b><br>Correlation: %{z:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(text="Correlation Matrix", 
                      font=dict(size=22, color='#2C3E50', family='Inter')),
            template='none',
            height=500,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=80, l=80, r=80),
            hoverlabel=dict(
                bgcolor='rgba(255, 255, 255, 0.95)', 
                bordercolor='#FF6B35', 
                font=dict(size=12, color='#2C3E50', family='Inter')
            ),
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(text="Error loading data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for solar wind vs flare activity
@app.callback(
    Output('solar-wind-flare', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date')]
)
def update_solar_wind_flare(start_date, end_date):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except Exception as e:
        raise PreventUpdate
    
    try:
        flare_daily = solar_flare_df.groupby('observation_date').agg({
            'flare_index': 'mean',
            'x_class_flares': 'sum',
            'm_class_flares': 'sum'
        }).reset_index()
        
        combined = pd.merge(
            flare_daily, 
            sunspot_df[['date', 'avg_solar_wind_speed']], 
            left_on='observation_date', 
            right_on='date', 
            how='inner'
        )
        
        combined_filtered = combined[
            (combined['observation_date'] >= start_date) & 
            (combined['observation_date'] <= end_date)
        ]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=combined_filtered['avg_solar_wind_speed'],
            y=combined_filtered['flare_index'],
            mode='markers',
            name='Flare Index vs Solar Wind',
            marker=dict(
                size=16,
                color=combined_filtered['x_class_flares'] + combined_filtered['m_class_flares'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="High-Class Flares", titlefont=dict(family='Inter')),
                line=dict(width=3, color='white')
            ),
            text=combined_filtered['observation_date'].dt.strftime('%Y-%m-%d'),
            hovertemplate='<b>%{text}</b><br>' +
                         'Solar Wind Speed: %{x:.1f} km/s<br>' +
                         'Flare Index: %{y:.2f}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(text="Solar Wind Speed vs Flare Activity", 
                      font=dict(size=22, color='#2C3E50', family='Inter')),
            xaxis=dict(
                title=dict(text="Average Solar Wind Speed (km/s)", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)', 
                showgrid=True,
                linecolor='rgba(255, 107, 53, 0.3)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Flare Index", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)', 
                showgrid=True,
                linecolor='rgba(255, 107, 53, 0.3)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            template='none',
            height=500,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=80, l=80, r=80),
            hoverlabel=dict(
                bgcolor='rgba(255, 255, 255, 0.95)', 
                bordercolor='#FF6B35', 
                font=dict(size=12, color='#2C3E50', family='Inter')
            ),
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(text="Error loading data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for solar region map
@app.callback(
    Output('solar-region-map', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date')]
)
def update_solar_region_map(start_date, end_date):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
    except Exception as e:
        raise PreventUpdate
    
    try:
        flare_filtered = solar_flare_df[
            (solar_flare_df['observation_date'] >= start_date) & 
            (solar_flare_df['observation_date'] <= end_date)
        ]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=flare_filtered['solar_longitude'],
            y=flare_filtered['solar_latitude'],
            mode='markers',
            name='Solar Regions',
            marker=dict(
                size=flare_filtered['region_area'] / 20,
                color=flare_filtered['flare_index'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Flare Index", titlefont=dict(family='Inter')),
                opacity=0.8,
                line=dict(width=3, color='white')
            ),
            text=flare_filtered['region_id'],
            hovertemplate='<b>%{text}</b><br>' +
                         'Latitude: %{y:.1f}°<br>' +
                         'Longitude: %{x:.1f}°<br>' +
                         'Region Area: ' + flare_filtered['region_area'].astype(str) + '<br>' +
                         'Flare Index: ' + flare_filtered['flare_index'].astype(str) + '<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(text="Solar Region Distribution", 
                      font=dict(size=22, color='#2C3E50', family='Inter')),
            xaxis=dict(
                title=dict(text="Solar Longitude (°)", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)', 
                showgrid=True,
                linecolor='rgba(255, 107, 53, 0.3)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Solar Latitude (°)", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)', 
                showgrid=True,
                linecolor='rgba(255, 107, 53, 0.3)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            template='none',
            height=500,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=80, l=80, r=80),
            hoverlabel=dict(
                bgcolor='rgba(255, 255, 255, 0.95)', 
                bordercolor='#FF6B35', 
                font=dict(size=12, color='#2C3E50', family='Inter')
            ),
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(text="Error loading data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)


# Enhanced metrics callback with interval component for real-time updates
@app.callback(
    [Output('total-flares', 'children'),
     Output('avg-sunspots', 'children'),
     Output('max-flare-index', 'children'),
     Output('active-regions', 'children'),
     Output('x-class-flares', 'children'),
     Output('solar-wind-speed', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')],
    prevent_initial_call=False
)
def update_metrics_enhanced(n_intervals, start_date, end_date, flare_classes, magnetic_types, sunspot_range, flare_occurred):
    """Enhanced real-time metrics update with interval component"""
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None filters
        if flare_classes is None or len(flare_classes) == 0:
            flare_classes = ['X', 'M', 'C']
        if magnetic_types is None or len(magnetic_types) == 0:
            magnetic_types = ['Alpha', 'Beta', 'Gamma', 'Delta']
        if sunspot_range is None or len(sunspot_range) < 2:
            sunspot_range = [float(solar_flare_df['sunspot_count'].min()), float(solar_flare_df['sunspot_count'].max())]
        if flare_occurred is None or len(flare_occurred) == 0:
            flare_occurred = [0, 1]
    except Exception as e:
        raise PreventUpdate
    
    try:
        # Filter data
        flare_filtered = solar_flare_df[
            (solar_flare_df['observation_date'] >= start_date) & 
            (solar_flare_df['observation_date'] <= end_date) &
            (solar_flare_df['magnetic_complexity'].isin(magnetic_types)) &
            (solar_flare_df['sunspot_count'] >= sunspot_range[0]) &
            (solar_flare_df['sunspot_count'] <= sunspot_range[1]) &
            (solar_flare_df['flare_occurred'].isin(flare_occurred))
        ].copy()
        
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date)
        ].copy()
        
        # Calculate diverse and meaningful metrics
        total_flares = flare_filtered['x_class_flares'].sum() + flare_filtered['m_class_flares'].sum() + flare_filtered['c_class_flares'].sum()
        avg_sunspots = sunspot_filtered['total_sunspots'].mean() if len(sunspot_filtered) > 0 else 0
        max_flare_index = flare_filtered['flare_index'].max() if len(flare_filtered) > 0 else 0
        active_regions = flare_filtered['region_id'].nunique() if len(flare_filtered) > 0 else 0
        m_class_flares = flare_filtered['m_class_flares'].sum()  # Changed from X-class to M-class
        solar_flux_avg = sunspot_filtered['solar_flux'].mean() if len(sunspot_filtered) > 0 else 0  # Changed from wind speed to solar flux
        
        return (f"{total_flares:,.0f}", f"{avg_sunspots:.0f}", f"{max_flare_index:.0f}", 
                f"{active_regions:,}", f"{m_class_flares:,.0f}", f"{solar_flux_avg:.0f}")
    except Exception as e:
        print(f"ERROR in update_metrics_enhanced: {str(e)}")
        return ("0", "0", "0", "0", "0", "0")

# Advanced Interactive Charts Callbacks


# Interactive Donut Chart
@app.callback(
    Output('magnetic-donut-chart', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_magnetic_donut_chart(start_date, end_date, flare_classes, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None filters
        if flare_classes is None or len(flare_classes) == 0:
            flare_classes = ['X', 'M', 'C']
        if magnetic_types is None or len(magnetic_types) == 0:
            magnetic_types = ['Alpha', 'Beta', 'Gamma', 'Delta']
        if sunspot_range is None or len(sunspot_range) < 2:
            sunspot_range = [float(solar_flare_df['sunspot_count'].min()), float(solar_flare_df['sunspot_count'].max())]
        if flare_occurred is None or len(flare_occurred) == 0:
            flare_occurred = [0, 1]
    except Exception as e:
        raise PreventUpdate
    
    try:
        # Filter sunspot data for solar cycle phases
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date) &
            (sunspot_df['total_sunspots'] >= sunspot_range[0]) &
            (sunspot_df['total_sunspots'] <= sunspot_range[1])
        ].copy()
        
        if len(sunspot_filtered) == 0:
            return go.Figure().add_annotation(text="No data available for selected filters", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Calculate solar cycle phases distribution
        cycle_counts = sunspot_filtered['solar_cycle_phase'].value_counts()
        
        # Sunrise Orange Theme for Solar Cycle Phases
        color_map = {
            'Rising': '#FF4500',    # Orange Red
            'Maximum': '#FF8C00',   # Dark Orange
            'Falling': '#FFA500',   # Orange
            'Minimum': '#FFD700'    # Gold
        }
        colors_list = [color_map.get(label, '#FF6B35') for label in cycle_counts.index]
        
        # Create interactive treemap
        fig = go.Figure(data=[go.Treemap(
            labels=cycle_counts.index,
            values=cycle_counts.values,
            parents=[''] * len(cycle_counts),
            marker=dict(
                colors=colors_list,
                line=dict(color='white', width=3)
            ),
            textinfo='label+value+percent parent',
            textfont=dict(size=14, color='white', family='Inter'),
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percentParent}<br><extra></extra>'
        )])
        
        fig.update_layout(
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=60, b=50, l=50, r=50),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(255, 107, 53, 0.3)',
                font=dict(size=10, color='#2C3E50', family='Inter')
            )
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_magnetic_donut_chart: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Interactive Bubble Chart
@app.callback(
    Output('solar-bubble-chart', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_solar_box_plot(start_date, end_date, flare_classes, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None filters
        if flare_classes is None or len(flare_classes) == 0:
            flare_classes = ['X', 'M', 'C']
        if magnetic_types is None or len(magnetic_types) == 0:
            magnetic_types = ['Alpha', 'Beta', 'Gamma', 'Delta']
        if sunspot_range is None or len(sunspot_range) < 2:
            sunspot_range = [float(solar_flare_df['sunspot_count'].min()), float(solar_flare_df['sunspot_count'].max())]
        if flare_occurred is None or len(flare_occurred) == 0:
            flare_occurred = [0, 1]
    except Exception as e:
        raise PreventUpdate
    
    try:
        # Filter data
        flare_filtered = solar_flare_df[
            (solar_flare_df['observation_date'] >= start_date) & 
            (solar_flare_df['observation_date'] <= end_date) &
            (solar_flare_df['magnetic_complexity'].isin(magnetic_types)) &
            (solar_flare_df['sunspot_count'] >= sunspot_range[0]) &
            (solar_flare_df['sunspot_count'] <= sunspot_range[1]) &
            (solar_flare_df['flare_occurred'].isin(flare_occurred))
        ].copy()
        
        if len(flare_filtered) == 0:
            return go.Figure().add_annotation(text="No data available for selected filters", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Sample data for bubble chart (reduced for performance)
        sample_data = flare_filtered.sample(min(100, len(flare_filtered)))
        
        # Beautiful Orange Theme for Solar Activity Bubble
        fig = go.Figure(data=[go.Scatter(
            x=sample_data['sunspot_count'],
            y=sample_data['flare_index'],
            mode='markers',
            marker=dict(
                size=sample_data['x_class_flares'] + sample_data['m_class_flares'] + sample_data['c_class_flares'],
                sizemode='diameter',
                sizeref=1.5,  # Smaller reference for larger bubbles
                color=sample_data['flare_index'],
                colorscale=[[0, '#FFF3E0'], [0.3, '#FFB74D'], [0.6, '#FF8A65'], [1, '#F7931E']],  # Orange gradient
                opacity=0.8,
                line=dict(width=3, color='white'),
                colorbar=dict(
                    title="Flare Index",
                    titlefont=dict(size=12, color='#F7931E', family='Inter'),
                    tickfont=dict(size=10, color='#F7931E', family='Inter')
                )
            ),
            text=sample_data['magnetic_complexity'],
            hovertemplate='<b>Sunspots:</b> %{x}<br><b>Flare Index:</b> %{y}<br><b>Total Flares:</b> %{marker.size}<br><b>Magnetic:</b> %{text}<br><extra></extra>'
        )])
        
        fig.update_layout(
            title=dict(text="Solar Activity Bubble Analysis", 
                      font=dict(size=20, color='#2C3E50', family='Inter')),
            xaxis=dict(
                title=dict(text="Sunspot Count", font=dict(size=16, color='#FF6B35', family='Inter')),
                color='#FF6B35', 
                gridcolor='rgba(255, 107, 53, 0.3)',
                linecolor='rgba(255, 107, 53, 0.8)',
                linewidth=2,
                tickfont=dict(size=14, color='#FF6B35', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Flare Index", font=dict(size=16, color='#FF6B35', family='Inter')),
                color='#FF6B35', 
                gridcolor='rgba(255, 107, 53, 0.3)',
                linecolor='rgba(255, 107, 53, 0.8)',
                linewidth=2,
                tickfont=dict(size=14, color='#FF6B35', family='Inter')
            ),
            template='none',
            height=600,  # Made larger
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=80, l=80, r=80)  # Increased margins for larger chart
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_solar_bubble_chart: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)


# Interactive Treemap
@app.callback(
    Output('solar-treemap', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_solar_violin_plot(start_date, end_date, flare_classes, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None filters
        if flare_classes is None or len(flare_classes) == 0:
            flare_classes = ['X', 'M', 'C']
        if magnetic_types is None or len(magnetic_types) == 0:
            magnetic_types = ['Alpha', 'Beta', 'Gamma', 'Delta']
        if sunspot_range is None or len(sunspot_range) < 2:
            sunspot_range = [float(solar_flare_df['sunspot_count'].min()), float(solar_flare_df['sunspot_count'].max())]
        if flare_occurred is None or len(flare_occurred) == 0:
            flare_occurred = [0, 1]
    except Exception as e:
        raise PreventUpdate
    
    try:
        # Filter data
        flare_filtered = solar_flare_df[
            (solar_flare_df['observation_date'] >= start_date) & 
            (solar_flare_df['observation_date'] <= end_date) &
            (solar_flare_df['magnetic_complexity'].isin(magnetic_types)) &
            (solar_flare_df['sunspot_count'] >= sunspot_range[0]) &
            (solar_flare_df['sunspot_count'] <= sunspot_range[1]) &
            (solar_flare_df['flare_occurred'].isin(flare_occurred))
        ].copy()
        
        if len(flare_filtered) == 0:
            return go.Figure().add_annotation(text="No data available for selected filters", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create treemap data
        magnetic_counts = flare_filtered['magnetic_complexity'].value_counts()
        
        # Create interactive treemap
        fig = go.Figure(go.Treemap(
            labels=magnetic_counts.index,
            values=magnetic_counts.values,
            parents=[''] * len(magnetic_counts),
            marker=dict(
                colors=['#FF6B35', '#F7931E', '#FF4444', '#4ECDC4'],
                line=dict(color='white', width=2)
            ),
            textinfo='label+value',
            textfont=dict(size=14, color='white', family='Inter'),
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br><extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(text="Activity Treemap", 
                      font=dict(size=16, color='#2C3E50', family='Inter')),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=60, b=50, l=50, r=50)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_solar_treemap: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Interactive Radar Chart
@app.callback(
    Output('solar-radar-chart', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_solar_bubble_chart(start_date, end_date, flare_classes, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None filters
        if flare_classes is None or len(flare_classes) == 0:
            flare_classes = ['X', 'M', 'C']
        if magnetic_types is None or len(magnetic_types) == 0:
            magnetic_types = ['Alpha', 'Beta', 'Gamma', 'Delta']
        if sunspot_range is None or len(sunspot_range) < 2:
            sunspot_range = [float(solar_flare_df['sunspot_count'].min()), float(solar_flare_df['sunspot_count'].max())]
        if flare_occurred is None or len(flare_occurred) == 0:
            flare_occurred = [0, 1]
    except Exception as e:
        raise PreventUpdate
    
    try:
        # Filter data
        flare_filtered = solar_flare_df[
            (solar_flare_df['observation_date'] >= start_date) & 
            (solar_flare_df['observation_date'] <= end_date) &
            (solar_flare_df['magnetic_complexity'].isin(magnetic_types)) &
            (solar_flare_df['sunspot_count'] >= sunspot_range[0]) &
            (solar_flare_df['sunspot_count'] <= sunspot_range[1]) &
            (solar_flare_df['flare_occurred'].isin(flare_occurred))
        ].copy()
        
        if len(flare_filtered) == 0:
            return go.Figure().add_annotation(text="No data available for selected filters", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create radar chart data
        categories = ['Sunspot Count', 'X-Class Flares', 'M-Class Flares', 'C-Class Flares', 'Flare Index']
        values = [
            flare_filtered['sunspot_count'].mean(),
            flare_filtered['x_class_flares'].mean(),
            flare_filtered['m_class_flares'].mean(),
            flare_filtered['c_class_flares'].mean(),
            flare_filtered['flare_index'].mean()
        ]
        
        # Normalize values for radar chart
        max_values = [flare_filtered['sunspot_count'].max(), 
                     flare_filtered['x_class_flares'].max(),
                     flare_filtered['m_class_flares'].max(),
                     flare_filtered['c_class_flares'].max(),
                     flare_filtered['flare_index'].max()]
        
        normalized_values = [v/max_v if max_v > 0 else 0 for v, max_v in zip(values, max_values)]
        
        # Create interactive radar chart
        fig = go.Figure(data=go.Scatterpolar(
            r=normalized_values + [normalized_values[0]],  # Close the shape
            theta=categories + [categories[0]],  # Close the shape
            fill='toself',
            fillcolor='rgba(255, 107, 53, 0.3)',
            line_color='#FF6B35',
            name='Solar Activity'
        ))
        
        fig.update_layout(
            title=dict(text="Multi-dimensional Radar", 
                      font=dict(size=16, color='#2C3E50', family='Inter')),
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    color='#2C3E50',
                    gridcolor='rgba(255, 107, 53, 0.15)'
                ),
                angularaxis=dict(
                    color='#2C3E50',
                    gridcolor='rgba(255, 107, 53, 0.15)'
                ),
                bgcolor='rgba(255, 255, 255, 0.1)'
            ),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=60, b=50, l=50, r=50)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_solar_radar_chart: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Interactive Candlestick Chart
@app.callback(
    Output('solar-candlestick-chart', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_solar_treemap(start_date, end_date, flare_classes, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None filters
        if flare_classes is None or len(flare_classes) == 0:
            flare_classes = ['X', 'M', 'C']
        if magnetic_types is None or len(magnetic_types) == 0:
            magnetic_types = ['Alpha', 'Beta', 'Gamma', 'Delta']
        if sunspot_range is None or len(sunspot_range) < 2:
            sunspot_range = [float(solar_flare_df['sunspot_count'].min()), float(solar_flare_df['sunspot_count'].max())]
        if flare_occurred is None or len(flare_occurred) == 0:
            flare_occurred = [0, 1]
    except Exception as e:
        raise PreventUpdate
    
    try:
        # Filter data
        flare_filtered = solar_flare_df[
            (solar_flare_df['observation_date'] >= start_date) & 
            (solar_flare_df['observation_date'] <= end_date) &
            (solar_flare_df['magnetic_complexity'].isin(magnetic_types)) &
            (solar_flare_df['sunspot_count'] >= sunspot_range[0]) &
            (solar_flare_df['sunspot_count'] <= sunspot_range[1]) &
            (solar_flare_df['flare_occurred'].isin(flare_occurred))
        ].copy()
        
        if len(flare_filtered) == 0:
            return go.Figure().add_annotation(text="No data available for selected filters", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create monthly candlestick data
        monthly_data = flare_filtered.groupby(flare_filtered['observation_date'].dt.to_period('M')).agg({
            'x_class_flares': ['sum', 'min', 'max'],
            'm_class_flares': ['sum', 'min', 'max'],
            'c_class_flares': ['sum', 'min', 'max'],
            'sunspot_count': ['mean', 'min', 'max']
        }).reset_index()
        
        monthly_data.columns = ['observation_date', 'x_open', 'x_low', 'x_high', 'm_open', 'm_low', 'm_high', 'c_open', 'c_low', 'c_high', 'sunspot_open', 'sunspot_low', 'sunspot_high']
        monthly_data['observation_date'] = monthly_data['observation_date'].dt.to_timestamp()
        
        # Take first 6 months for candlestick (reduced for performance)
        candlestick_data = monthly_data.head(6)
        
        # Create interactive candlestick chart
        fig = go.Figure(data=go.Candlestick(
            x=candlestick_data['observation_date'],
            open=candlestick_data['sunspot_open'],
            high=candlestick_data['sunspot_high'],
            low=candlestick_data['sunspot_low'],
            close=candlestick_data['sunspot_open'],  # Using open as close for simplicity
            increasing_line_color='#FF6B35',
            decreasing_line_color='#F7931E',
            name='Sunspot Activity'
        ))
        
        fig.update_layout(
            title=dict(text="Activity Candlestick", 
                      font=dict(size=16, color='#2C3E50', family='Inter')),
            xaxis=dict(
                title=dict(text="Month", font=dict(size=12, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)',
                tickfont=dict(size=10, color='#2C3E50', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Sunspot Count", font=dict(size=12, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)',
                tickfont=dict(size=10, color='#2C3E50', family='Inter')
            ),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=60, b=50, l=60, r=50)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_solar_candlestick_chart: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Anomaly Detection
@app.callback(
    Output('anomaly-detection', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_anomaly_detection(start_date, end_date, flare_classes, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Handle None dates
        if start_date is None:
            start_date = solar_flare_df['observation_date'].min()
        if end_date is None:
            end_date = solar_flare_df['observation_date'].max()
        
        # Convert to datetime if strings
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        # Handle None filters
        if flare_classes is None or len(flare_classes) == 0:
            flare_classes = ['X', 'M', 'C']
        if magnetic_types is None or len(magnetic_types) == 0:
            magnetic_types = ['Alpha', 'Beta', 'Gamma', 'Delta']
        if sunspot_range is None or len(sunspot_range) < 2:
            sunspot_range = [float(solar_flare_df['sunspot_count'].min()), float(solar_flare_df['sunspot_count'].max())]
        if flare_occurred is None or len(flare_occurred) == 0:
            flare_occurred = [0, 1]
    except Exception as e:
        raise PreventUpdate
    
    try:
        # Filter data
        flare_filtered = solar_flare_df[
            (solar_flare_df['observation_date'] >= start_date) & 
            (solar_flare_df['observation_date'] <= end_date) &
            (solar_flare_df['magnetic_complexity'].isin(magnetic_types)) &
            (solar_flare_df['sunspot_count'] >= sunspot_range[0]) &
            (solar_flare_df['sunspot_count'] <= sunspot_range[1]) &
            (solar_flare_df['flare_occurred'].isin(flare_occurred))
        ].copy()
        
        if len(flare_filtered) == 0:
            return go.Figure().add_annotation(text="No data available for selected filters", 
                                            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Calculate total flares
        flare_filtered['total_flares'] = flare_filtered['x_class_flares'] + flare_filtered['m_class_flares'] + flare_filtered['c_class_flares']
        
        # Simple anomaly detection using IQR method
        Q1 = flare_filtered['total_flares'].quantile(0.25)
        Q3 = flare_filtered['total_flares'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Identify anomalies
        flare_filtered['is_anomaly'] = (flare_filtered['total_flares'] < lower_bound) | (flare_filtered['total_flares'] > upper_bound)
        
        # Create the plot
        fig = go.Figure()
        
        # Normal data points
        normal_data = flare_filtered[~flare_filtered['is_anomaly']]
        fig.add_trace(go.Scatter(
            x=normal_data['observation_date'],
            y=normal_data['total_flares'],
            mode='markers',
            name='Normal',
            marker=dict(color='#2E8B57', size=6),
            hovertemplate='<b>Date:</b> %{x}<br><b>Total Flares:</b> %{y}<br><extra></extra>'
        ))
        
        # Anomaly data points
        anomaly_data = flare_filtered[flare_filtered['is_anomaly']]
        if len(anomaly_data) > 0:
            fig.add_trace(go.Scatter(
                x=anomaly_data['observation_date'],
                y=anomaly_data['total_flares'],
                mode='markers',
                name='Anomaly',
                marker=dict(color='#FF4444', size=10, symbol='diamond'),
                hovertemplate='<b>Date:</b> %{x}<br><b>Total Flares:</b> %{y}<br><b>Status:</b> Anomaly<br><extra></extra>'
            ))
        
        # Add threshold lines
        fig.add_hline(y=upper_bound, line_dash="dash", line_color="red", 
                     annotation_text=f"Upper Threshold: {upper_bound:.1f}")
        fig.add_hline(y=lower_bound, line_dash="dash", line_color="red", 
                     annotation_text=f"Lower Threshold: {lower_bound:.1f}")
        
        fig.update_layout(
            title=dict(text="Anomaly Detection", 
                      font=dict(size=18, color='#2C3E50', family='Inter')),
            xaxis=dict(
                title=dict(text="Date", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Total Flares", font=dict(size=14, color='#2C3E50', family='Inter')),
                color='#2C3E50', 
                gridcolor='rgba(255, 107, 53, 0.15)',
                tickfont=dict(size=12, color='#2C3E50', family='Inter')
            ),
            template='none',
            height=500,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            legend=dict(
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(255, 107, 53, 0.3)',
                font=dict(size=12, color='#2C3E50', family='Inter')
            ),
            margin=dict(t=80, b=60, l=80, r=80)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_anomaly_detection: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for Solar Activity Heatmap
@app.callback(
    Output('solar-heatmap', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('cycle-phase-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_solar_heatmap(start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Apply filters
        flare_filtered = apply_filters(solar_flare_df, start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred)
        
        if len(flare_filtered) == 0:
            return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create monthly heatmap data
        flare_filtered['month'] = flare_filtered['observation_date'].dt.month
        flare_filtered['year'] = flare_filtered['observation_date'].dt.year
        
        # Aggregate data for heatmap
        heatmap_data = flare_filtered.groupby(['year', 'month']).agg({
            'total_flares': 'sum',
            'x_class_flares': 'sum',
            'm_class_flares': 'sum',
            'c_class_flares': 'sum'
        }).reset_index()
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data['total_flares'],
            x=heatmap_data['month'],
            y=heatmap_data['year'],
            colorscale=[[0, '#FFF3E0'], [0.3, '#FFB74D'], [0.6, '#FF8A65'], [1, '#FF6B35']],
            hovertemplate='<b>Year:</b> %{y}<br><b>Month:</b> %{x}<br><b>Total Flares:</b> %{z}<br><extra></extra>',
            colorbar=dict(
                title="Total Flares",
                titlefont=dict(size=12, color='#FF6B35', family='Inter'),
                tickfont=dict(size=10, color='#FF6B35', family='Inter')
            )
        ))
        
        fig.update_layout(
            title=dict(text="Solar Activity Heatmap", 
                      font=dict(size=18, color='#2C3E50', family='Inter')),
            xaxis=dict(
                title=dict(text="Month", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                tickmode='linear',
                tick0=1,
                dtick=1,
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Year", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=60, l=80, r=80)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_solar_heatmap: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for Flare Intensity Histogram
@app.callback(
    Output('flare-intensity-histogram', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('cycle-phase-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_flare_intensity_histogram(start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Apply filters
        flare_filtered = apply_filters(solar_flare_df, start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred)
        
        if len(flare_filtered) == 0:
            return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create intensity categories
        intensity_bins = [0, 10, 25, 50, 100, 200, 500, 1000]
        intensity_labels = ['0-10', '11-25', '26-50', '51-100', '101-200', '201-500', '501-1000']
        
        flare_filtered['intensity_bin'] = pd.cut(flare_filtered['total_flares'], bins=intensity_bins, labels=intensity_labels, include_lowest=True)
        intensity_counts = flare_filtered['intensity_bin'].value_counts().sort_index()
        
        # Beautiful Blue Theme for Histogram
        fig = go.Figure(data=[go.Bar(
            x=intensity_counts.index,
            y=intensity_counts.values,
            marker=dict(
                color=['#3498DB', '#5DADE2', '#85C1E9', '#AED6F1', '#D6EAF8', '#EBF5FB', '#F8F9FA'],
                line=dict(color='white', width=2)
            ),
            hovertemplate='<b>Intensity Range:</b> %{x}<br><b>Count:</b> %{y}<br><extra></extra>',
            text=intensity_counts.values,
            textposition='auto',
            textfont=dict(size=12, color='white', family='Inter')
        )])
        
        fig.update_layout(
            title=dict(text="Flare Intensity Distribution", 
                      font=dict(size=18, color='#2C3E50', family='Inter')),
            xaxis=dict(
                title=dict(text="Flare Intensity Range", font=dict(size=14, color='#3498DB', family='Inter')),
                color='#3498DB',
                tickfont=dict(size=12, color='#3498DB', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Count", font=dict(size=14, color='#3498DB', family='Inter')),
                color='#3498DB',
                gridcolor='rgba(52, 152, 219, 0.2)',
                tickfont=dict(size=12, color='#3498DB', family='Inter')
            ),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=60, l=80, r=80)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_flare_intensity_histogram: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for Solar Activity Area Chart
@app.callback(
    Output('solar-activity-area', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('cycle-phase-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_solar_activity_area(start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Apply filters to sunspot data
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date)
        ].copy()
        
        if len(sunspot_filtered) == 0:
            return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create solar wind data from sunspot data using existing columns
        wind_pressure_data = sunspot_filtered.groupby(sunspot_filtered['date'].dt.to_period('M')).agg({
            'avg_solar_wind_speed': 'mean',
            'geomagnetic_index': 'mean',
            'temperature_variation': 'mean'
        }).reset_index()
        
        wind_pressure_data['date'] = wind_pressure_data['date'].dt.to_timestamp()
        
        # Beautiful Orange Theme for Solar Activity Categories - Pie Chart
        # Create activity categories based on solar wind speed
        wind_pressure_data['activity_category'] = pd.cut(
            wind_pressure_data['avg_solar_wind_speed'], 
            bins=[0, 300, 400, 500, float('inf')], 
            labels=['Low Activity', 'Medium Activity', 'High Activity', 'Very High Activity']
        )
        
        # Count categories
        category_counts = wind_pressure_data['activity_category'].value_counts()
        
        # Sunrise Orange Theme for Activity Categories
        color_map = {
            'Low Activity': '#FFD700',      # Gold
            'Medium Activity': '#FFB347',   # Peach
            'High Activity': '#FFA500',     # Orange
            'Very High Activity': '#FF8C00' # Dark Orange
        }
        colors_list = [color_map.get(label, '#FF6B35') for label in category_counts.index]
        
        # Create pie chart
        fig = go.Figure(data=[go.Pie(
            labels=category_counts.index,
            values=category_counts.values,
            marker_colors=colors_list,
            textinfo='label+value+percent',
            textfont_size=14,
            textfont_color='white',
            textfont_family='Inter',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<br><extra></extra>',
            marker_line=dict(color='white', width=2),
            rotation=0,
            pull=[0.1, 0.05, 0.05, 0.05],
            textposition='inside'
        )])
        
        fig.update_layout(
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=60, l=60, r=60),
            hovermode='x unified'
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_solar_activity_area: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for Flare Intensity Bar Chart
@app.callback(
    Output('flare-intensity-bar', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('cycle-phase-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_flare_intensity_bar(start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Apply filters to sunspot data
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date)
        ].copy()
        
        if len(sunspot_filtered) == 0:
            return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create solar flux data for box plot
        flux_data = sunspot_filtered.groupby(sunspot_filtered['date'].dt.to_period('M')).agg({
            'solar_flux': 'mean',
            'total_sunspots': 'mean'
        }).reset_index()
        
        # Create solar flux bins for box plot
        flux_bins = pd.cut(flux_data['solar_flux'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
        flux_data['flux_level'] = flux_bins
        
        # Beautiful Orange Theme for Solar Flux Box Plot
        fig = go.Figure()
        
        for level in ['Very Low', 'Low', 'Medium', 'High', 'Very High']:
            level_data = flux_data[flux_data['flux_level'] == level]['solar_flux'].dropna()
            if len(level_data) > 0:
                fig.add_trace(go.Box(
                    y=level_data,
                    name=level,
                    marker_color='#FF6B35',
                    marker_line=dict(color='white', width=2),
                    boxpoints='outliers',
                    hovertemplate=f'<b>{level}</b><br>Solar Flux: %{{y}}<br>Count: %{{customdata}}<extra></extra>',
                    customdata=[len(level_data)] * len(level_data)
                ))
        
        fig.update_layout(
            xaxis=dict(
                title=dict(text="Solar Flux Level", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                gridcolor='rgba(255, 107, 53, 0.2)',
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Solar Flux Value", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                gridcolor='rgba(255, 107, 53, 0.2)',
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=60, l=60, r=60)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_flare_intensity_bar: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for Solar Wind Speed Analysis
@app.callback(
    Output('solar-wind-chart', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('cycle-phase-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_solar_wind_chart(start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Apply filters to sunspot data
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date)
        ].copy()
        
        if len(sunspot_filtered) == 0:
            return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create geomagnetic index data from sunspot data
        geomagnetic_data = sunspot_filtered.groupby(sunspot_filtered['date'].dt.to_period('M')).agg({
            'geomagnetic_index': 'mean',
            'total_sunspots': 'mean',
            'solar_flux': 'mean'
        }).reset_index()
        
        geomagnetic_data['date'] = geomagnetic_data['date'].dt.to_timestamp()
        
        # Beautiful Orange Theme for Geomagnetic Index - Enhanced Box Plot
        # Prepare data for better year comparison
        geomagnetic_data_sorted = geomagnetic_data.sort_values('date')
        geomagnetic_data_sorted['year'] = geomagnetic_data_sorted['date'].dt.year
        
        # Group by year for better comparison
        years = sorted(geomagnetic_data_sorted['year'].unique())
        
        fig = go.Figure()
        
        # Create distinct colors for each year - Sunrise Orange Theme
        colors = ['#FF4500', '#FF8C00', '#FFA500', '#FFB347', '#FFD700', '#FFF8DC']
        
        for i, year in enumerate(years):
            year_data = geomagnetic_data_sorted[geomagnetic_data_sorted['year'] == year]['geomagnetic_index']
            if len(year_data) > 0:
                fig.add_trace(go.Box(
                    y=year_data,
                    name=str(year),
                    boxpoints='outliers',
                    jitter=0.3,
                    pointpos=-1.8,
                    fillcolor=colors[i % len(colors)],
                    line_color='#FF6B35',
                    marker=dict(
                        color='#FF6B35',
                        line=dict(color='white', width=1),
                        size=8
                    ),
                    hovertemplate=f'<b>Year: {year}</b><br>Geomagnetic Index: %{{y:.2f}}<br>Count: {len(year_data)}<extra></extra>'
                ))
        
        fig.update_layout(
            xaxis=dict(
                title=dict(text="Year", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                gridcolor='rgba(255, 107, 53, 0.2)',
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Geomagnetic Index", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                gridcolor='rgba(255, 107, 53, 0.2)',
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=60, l=60, r=60)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_solar_wind_chart: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)

# Callback for Flare Energy Distribution
@app.callback(
    Output('flare-energy-chart', 'figure'),
    [Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('flare-class-filter', 'value'),
     Input('cycle-phase-filter', 'value'),
     Input('magnetic-complexity-filter', 'value'),
     Input('sunspot-count-slider', 'value'),
     Input('flare-occurred-filter', 'value')]
)
def update_flare_energy_chart(start_date, end_date, flare_classes, cycle_phases, magnetic_types, sunspot_range, flare_occurred):
    try:
        # Apply filters to sunspot data
        sunspot_filtered = sunspot_df[
            (sunspot_df['date'] >= start_date) & 
            (sunspot_df['date'] <= end_date)
        ].copy()
        
        if len(sunspot_filtered) == 0:
            return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        
        # Create temperature variation data from sunspot data
        temp_data = sunspot_filtered.groupby(sunspot_filtered['date'].dt.to_period('M')).agg({
            'temperature_variation': 'mean',
            'total_sunspots': 'mean'
        }).reset_index()
        
        temp_data['date'] = temp_data['date'].dt.to_timestamp()
        
        # Create temperature variation vertical bar chart over time
        temp_data_sorted = temp_data.sort_values('date')
        
        # Prepare data for vertical bar chart
        temp_data_sorted['year'] = temp_data_sorted['date'].dt.year
        temp_data_sorted['month'] = temp_data_sorted['date'].dt.month
        
        # Group by year for vertical bar chart
        yearly_temp = temp_data_sorted.groupby('year')['temperature_variation'].mean().reset_index()
        
        # Beautiful Orange Theme for Temperature Chart - Vertical Bar Chart
        fig = go.Figure(data=[go.Bar(
            x=yearly_temp['year'],
            y=yearly_temp['temperature_variation'],
            name='Temperature Variation',
            marker_color='#FF6B35',
            marker_line=dict(color='white', width=2),
            hovertemplate='<b>Year:</b> %{x}<br><b>Temperature Variation:</b> %{y:.2f}<extra></extra>'
        )])
        
        fig.update_layout(
            xaxis=dict(
                title=dict(text="Year", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                gridcolor='rgba(255, 107, 53, 0.2)',
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            yaxis=dict(
                title=dict(text="Temperature Variation", font=dict(size=14, color='#FF6B35', family='Inter')),
                color='#FF6B35',
                gridcolor='rgba(255, 107, 53, 0.2)',
                tickfont=dict(size=12, color='#FF6B35', family='Inter')
            ),
            template='none',
            height=400,
            plot_bgcolor='rgba(255, 255, 255, 0.1)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', color='#2C3E50'),
            margin=dict(t=80, b=60, l=60, r=60)
        )
        
        return fig
    except Exception as e:
        print(f"ERROR in update_flare_energy_chart: {str(e)}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)


if __name__ == '__main__':
        print("Starting Solar Activity Dashboard...")
        print("Dashboard features:")
        print("   • 9 Beautiful Orange-Themed Interactive Visualizations")
        print("   • Real-time updates every 30 seconds")
        print("   • 2x3 Grid Layout + Large Timeline + 1x2 Bottom Row")
        print("   • Flare Class Distribution (Donut Chart)")
        print("   • Solar Cycle Phases (Treemap)")
        print("   • Geomagnetic Index Analysis (Violin Plot)")
        print("   • Temperature Variation Over Time (Vertical Bar Chart)")
        print("   • Solar Activity Trends (Radar Chart)")
        print("   • Solar Flux Levels (Box Plot)")
        print("   • Sunspot Activity Timeline (Large Full-Width Line Chart)")
        print("   • Solar Wind Speed Analysis (Area Chart)")
        print("   • Solar Irradiance Distribution (Horizontal Bar Chart)")
        print("   • All charts show DIFFERENT metrics and measurements")
        print("   • Optimized performance and memory usage")
        print("   • Professional glassmorphic design with unified orange theme")
        print("Access at: http://127.0.0.1:8055/")
        app.run(debug=False, host='127.0.0.1', port=8055, threaded=True)
