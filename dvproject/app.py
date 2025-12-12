"""
Pakistan District Development Dashboard
=========================================

Interactive Streamlit dashboard displaying Pakistan's district-level
development indicators across 11 dimensions using weighted composite scores.

Run: streamlit run app.py
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Pakistan District Development Atlas",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #2c3e50;
        text-align: center;
        margin-top: 0;
        margin-bottom: 0.2rem;
        padding-top: 0;
    }
    .sub-header {
        font-size: 0.85rem;
        color: #7f8c8d;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #3498db;
        margin-bottom: 1rem;
    }
    .dimension-tag {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        margin: 0.2rem;
        background-color: #e8f4f8;
        border-radius: 15px;
        font-size: 0.85rem;
        color: #2980b9;
    }
    /* Hide scrollbar for Concise and Multiple Pages modes */
    .no-scroll {
        overflow: hidden !important;
        height: 100vh !important;
    }
    /* Header styling */
    .header-container {
        background-color: #f8f9fa;
        padding: 1rem 2rem;
        border-bottom: 2px solid #e0e0e0;
        margin-bottom: 0;
    }
    .header-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #2c3e50;
        margin: 0;
        padding: 0;
    }
    .header-subtitle {
        font-size: 0.85rem;
        color: #7f8c8d;
        margin: 0.2rem 0 0 0;
        padding: 0;
    }
    </style>
""", unsafe_allow_html=True)

# Header with title on left and dropdown on right
st.markdown('<div class="header-container">', unsafe_allow_html=True)
header_left, header_right = st.columns([7, 3])

with header_left:
    st.markdown('''
    <div class="header-title">Pakistan District Development Atlas</div>
    <div class="header-subtitle">Comprehensive Multi-Dimensional Analysis of 138 Districts Across Pakistan</div>
    ''', unsafe_allow_html=True)

with header_right:
    layout_mode = st.selectbox(
        "View Mode",
        ["Vertical Scroll", "Concise Dashboard", "Multiple Pages"],
        index=1,  # Default to Concise Dashboard
        help="Choose how to view visualizations",
        label_visibility="visible"
    )

st.markdown('</div>', unsafe_allow_html=True)

# Initialize session state for page navigation
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

# Define all visualizations as functions
def render_choropleth_map(compact=False):
    """Render the choropleth map"""
    if not compact:
        st.markdown("<h4 style='font-size: 1.1rem; margin-bottom: 0.5rem;'>District Development Choropleth Map</h4>", unsafe_allow_html=True)
    
    map_file = Path("pakistan_all_layers_choropleth.html")
    if map_file.exists():
        with open(map_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        height = 400 if compact else 550
        components.html(html_content, height=height, scrolling=False)
    else:
        st.error("❌ Map file not found! Run: `python generate_choropleth_maps.py`")

def render_radar_chart(compact=False):
    """Render the provincial radar chart"""
    if not compact:
        st.markdown("<h4 style='font-size: 1.1rem; margin-bottom: 0.3rem;'>Provincial Development Radar Chart</h4>", unsafe_allow_html=True)
    
    if not Path("Mouza_Census_PCADimension.csv").exists():
        st.warning("Data file not found. Please ensure `Mouza_Census_PCADimension.csv` exists.")
        return
    
    df_radar = pd.read_csv("Mouza_Census_PCADimension.csv")
    index_cols = [col for col in df_radar.columns if '_Index' in col]
    df_radar['Composite_Score'] = df_radar[index_cols].mean(axis=1)
    
    province_colors = {
        'PUNJAB': '#2e7d32',
        'SINDH': '#ec407a',
        'BALOCHISTAN': '#ff6f00',
        'KHYBER PAKHTUNKHWA': '#795548',
        'AZAD JAMMU AND KASHMIR': '#1976d2',
        'GILGIT BALTISTAN': '#7b1fa2',
        'ISLAMABAD CAPITAL TERRITORY': '#c62828'
    }
    
    province_avg_scores = df_radar.groupby('Name of Province')['Composite_Score'].mean().sort_values(ascending=False)
    all_provinces = province_avg_scores.index.tolist()
    selected_provinces = all_provinces
    
    dimension_names = [col.replace('_Index', '').replace('_', ' ') for col in index_cols]
    province_ranks = {prov: idx for idx, prov in enumerate(all_provinces)}
    
    # Calculate dynamic comparative metrics
    # 1. Overall leader
    leader_province = province_avg_scores.index[0]
    leader_score = province_avg_scores.iloc[0]
    
    # 2. Biggest improvement opportunity (largest gap below national average)
    national_avg_composite = df_radar['Composite_Score'].mean()
    province_gaps = province_avg_scores - national_avg_composite
    improvement_province = province_gaps.idxmin()
    improvement_gap = abs(province_gaps.min())
    
    # 3. Most consistent performer (smallest variance across dimensions)
    province_variances = {}
    for prov in all_provinces:
        if prov in df_radar['Name of Province'].values:
            prov_data = df_radar[df_radar['Name of Province'] == prov]
            prov_values = prov_data[index_cols].mean().values
            province_variances[prov] = prov_values.std()
    
    most_consistent = min(province_variances, key=province_variances.get)
    consistency_score = province_variances[most_consistent]
    
    fig = go.Figure()
    
    # National Average
    nat_values = df_radar[index_cols].mean().values.tolist()
    nat_values.append(nat_values[0])
    
    fig.add_trace(go.Scatterpolar(
        r=nat_values,
        theta=dimension_names + [dimension_names[0]],
        fill='toself',
        name='National Average',
        line=dict(color='black', width=2.5, dash='dash'),
        fillcolor='rgba(0, 0, 0, 0.1)',
        opacity=0.9,
        marker=dict(size=6)
    ))
    
    # Add provinces
    for prov in selected_provinces:
        if prov in df_radar['Name of Province'].values:
            prov_data = df_radar[df_radar['Name of Province'] == prov]
            values = prov_data[index_cols].mean().values.tolist()
            values.append(values[0])
            
            color = province_colors.get(prov, '#95a5a6')
            hex_color = color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            fill_color = f'rgba({r}, {g}, {b}, 0.08)'
            
            rank = province_ranks.get(prov, 999)
            linewidth = 2 if rank < 3 else 1.5
            opacity = 0.8 if rank < 3 else 0.6
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=dimension_names + [dimension_names[0]],
                fill='toself',
                name=prov,
                line=dict(color=color, width=linewidth),
                fillcolor=fill_color,
                opacity=opacity,
                marker=dict(size=4)
            ))
    
    chart_height = 500 if compact else 650
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 90],
                tickmode='array',
                tickvals=[20, 40, 60, 80, 90],
                ticktext=['20', '40', '60', '80', '90'],
                showline=True,
                linewidth=0.8,
                gridcolor='rgba(0, 0, 0, 0.25)',
                gridwidth=1
            ),
            angularaxis=dict(
                direction='clockwise',
                rotation=90,
                tickfont=dict(size=12, family='Arial, sans-serif')
            )
        ),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.97,
            xanchor="left",
            x=1.05,
            font=dict(size=11),
            bordercolor='gray',
            borderwidth=1,
            itemclick='toggle',
            itemdoubleclick='toggleothers',
            bgcolor='rgba(255, 255, 255, 0.9)',
            title=dict(
                text='<span style="font-weight:normal; font-size:10px;">Click to toggle</span>',
                font=dict(size=10, color='#7f8c8d')
            )
        ),
        height=chart_height,
        margin=dict(l=100, r=250, t=100, b=100),
        title=dict(
            text="Comprehensive Development Radar",
            font=dict(size=13, color='#2c3e50', family='Arial, sans-serif'),
            x=0.45,
            xanchor='center',
            y=0.98,
            yanchor='top'
        ),
        annotations=[
            dict(
                text='<b>Territories</b>',
                x=1.05,
                y=1.02,
                xref='paper',
                yref='paper',
                xanchor='left',
                yanchor='bottom',
                showarrow=False,
                font=dict(size=10, color='#2c3e50', family='Arial, sans-serif')
            ),
            dict(
                text=(
                    f"<b>Key Insights:</b><br>"
                    f"🏆 Leader: <b>{leader_province}</b> ({leader_score:.1f})<br>"
                    f"📈 Needs Focus: <b>{improvement_province}</b> ({improvement_gap:.1f} below avg)<br>"
                    f"⚖️ Most Balanced: <b>{most_consistent}</b> (σ={consistency_score:.1f})"
                ),
                x=0.98,
                y=0.35,
                xref='paper',
                yref='paper',
                xanchor='left',
                yanchor='top',
                showarrow=False,
                font=dict(size=9.5, color='#34495e', family='Arial, sans-serif'),
                bgcolor='rgba(236, 240, 241, 0.9)',
                bordercolor='#95a5a6',
                borderwidth=1,
                borderpad=6
            )
        ],
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToAdd': ['resetScale2d'],
        'modeBarButtonsToRemove': [],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'pakistan_provincial_radar_chart',
            'height': 800,
            'width': 1200,
            'scale': 2
        }
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)

def render_provincial_bar_chart(compact=False):
    """Render the provincial development bar chart with custom weighted scores"""
    if not compact:
        st.markdown("<h4 style='font-size: 1rem; margin-bottom: 1rem; margin-top: 1.5rem;'>Provincial Development Rankings</h4>", unsafe_allow_html=True)
    
    if not Path("Mouza_Census_PCADimension.csv").exists():
        st.warning("Data file not found. Please ensure `Mouza_Census_PCADimension.csv` exists.")
        return
    
    df_bar = pd.read_csv("Mouza_Census_PCADimension.csv")
    index_cols = [col for col in df_bar.columns if '_Index' in col]
    
    # Define custom weights for each dimension
    custom_weights = {
        'Settlement_Index': 0.10,
        'Agriculture_Livestock_Index': 0.12,
        'Housing_Amenities_Index': 0.10,
        'Infrastructure_Services_Index': 0.12,
        'Education_Index': 0.15,
        'Health_Index': 0.15,
        'Recreation_Sports_Index': 0.05,
        'Social_Community_Index': 0.06,
        'Industry_Index': 0.08,
        'Credit_Finance_Index': 0.05,
        'Disaster_Resilience_Index': 0.02
    }
    
    # Calculate custom weighted score
    df_bar['Custom_Weighted_Score'] = sum(df_bar[col] * custom_weights[col] for col in index_cols)
    
    province_colors = {
        'PUNJAB': '#2e7d32',
        'SINDH': '#ec407a',
        'BALOCHISTAN': '#ff6f00',
        'KHYBER PAKHTUNKHWA': '#795548',
        'AZAD JAMMU AND KASHMIR': '#1976d2',
        'GILGIT BALTISTAN': '#7b1fa2',
        'ISLAMABAD CAPITAL TERRITORY': '#c62828'
    }
    
    # Calculate provincial statistics
    province_stats = df_bar.groupby('Name of Province')['Custom_Weighted_Score'].mean().sort_values(ascending=False)
    national_avg = df_bar['Custom_Weighted_Score'].mean()
    
    # Calculate additional provincial context for tooltips
    province_context = {}
    for province in province_stats.index:
        prov_data = df_bar[df_bar['Name of Province'] == province]
        
        # Get district count
        district_count = len(prov_data)
        
        # Calculate dimension averages for this province
        dim_avgs = {col.replace('_Index', '').replace('_', ' '): prov_data[col].mean() 
                    for col in index_cols}
        
        # Find strongest and weakest dimensions
        strongest_dim = max(dim_avgs.items(), key=lambda x: x[1])
        weakest_dim = min(dim_avgs.items(), key=lambda x: x[1])
        
        province_context[province] = {
            'districts': district_count,
            'strongest': strongest_dim,
            'weakest': weakest_dim
        }
    
    # Calculate quartiles for gap analysis
    q25 = province_stats.quantile(0.25)
    q50 = province_stats.quantile(0.50)
    q75 = province_stats.quantile(0.75)
    
    # Calculate development gap
    top_score = province_stats.iloc[0]
    bottom_score = province_stats.iloc[-1]
    dev_gap = top_score - bottom_score
    
    # Add spacing before chart
    st.markdown("<div style='margin-bottom: 0.8rem;'></div>", unsafe_allow_html=True)
    
    # Create bar chart
    fig = go.Figure()
    
    colors = [province_colors.get(prov, '#95a5a6') for prov in province_stats.index]
    
    # Enhanced hover templates with provincial context
    hover_texts = []
    for prov in province_stats.index:
        ctx = province_context[prov]
        hover_text = (
            f"<b>{prov}</b><br>"
            f"Average Score: {province_stats[prov]:.2f}<br>"
            f"<br>"
            f"Districts: {ctx['districts']}<br>"
            f"Strongest: {ctx['strongest'][0]} ({ctx['strongest'][1]:.1f})<br>"
            f"Weakest: {ctx['weakest'][0]} ({ctx['weakest'][1]:.1f})"
        )
        hover_texts.append(hover_text)
    
    fig.add_trace(go.Bar(
        x=province_stats.index,
        y=province_stats.values,
        marker=dict(
            color=colors,
            opacity=0.8,
            line=dict(color='black', width=2)
        ),
        text=[f'{v:.1f}' for v in province_stats.values],
        textposition='outside',
        textfont=dict(size=11, color='#2c3e50', family='Arial, sans-serif', weight='bold'),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hover_texts,
        showlegend=False
    ))
    
    # Add national average line
    fig.add_hline(
        y=national_avg,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"National Average: {national_avg:.1f}",
        annotation_position="top right",
        annotation_font_size=10,
        annotation_font_color="red"
    )
    
    # Add development gap annotation
    fig.add_annotation(
        x=0.5,
        y=1.05,
        xref='paper',
        yref='paper',
        text=f"<b>Development Gap:</b> {dev_gap:.1f} points ({province_stats.index[0]} vs {province_stats.index[-1]})",
        showarrow=False,
        font=dict(size=11, color='#c62828'),
        bgcolor='rgba(255, 235, 238, 0.8)',
        bordercolor='#c62828',
        borderwidth=1,
        borderpad=4
    )
    
    # Add invisible trace for legend (national average)
    fig.add_trace(go.Scatter(
        x=[None],
        y=[None],
        mode='lines',
        line=dict(color='red', width=2, dash='dash'),
        name=f'National Average: {national_avg:.1f}',
        showlegend=True
    ))
    
    chart_height = 550 if compact else 700
    
    fig.update_layout(
        title=dict(
            text="Province by Average Weighted Development Score",
            font=dict(size=14 if not compact else 13, color='#2c3e50', family='Arial, sans-serif', weight='bold'),
            x=0.5,
            xanchor='center',
            y=0.92,
            yanchor='top',
            pad=dict(b=10, t=0)
        ),
        xaxis=dict(
            title="",
            tickangle=-45,
            tickfont=dict(size=11)
        ),
        yaxis=dict(
            title=dict(
                text="Average Custom Weighted Score",
                font=dict(size=12, weight='bold')
            ),
            tickfont=dict(size=10),
            gridcolor='rgba(0, 0, 0, 0.3)',
            showgrid=True
        ),
        height=chart_height,
        margin=dict(l=70, r=40, t=130, b=120),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=True,
        legend=dict(
            x=0.98,
            y=0.98,
            xanchor='right',
            yanchor='top',
            font=dict(size=10),
            bgcolor='rgba(255, 255, 255, 0.9)',
            bordercolor='gray',
            borderwidth=1
        )
    )
    
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'pakistan_provincial_weighted_comparison',
            'height': 600,
            'width': 1000,
            'scale': 2
        }
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)

def render_provincial_boxplot(compact=False):
    """Render the provincial box plot showing distribution of weighted scores"""
    if not compact:
        st.markdown("<h4 style='font-size: 1rem; margin-bottom: 1rem; margin-top: 1.5rem;'>Provincial Score Distribution</h4>", unsafe_allow_html=True)
    
    if not Path("Mouza_Census_PCADimension.csv").exists():
        st.warning("Data file not found. Please ensure `Mouza_Census_PCADimension.csv` exists.")
        return
    
    df_box = pd.read_csv("Mouza_Census_PCADimension.csv")
    index_cols = [col for col in df_box.columns if '_Index' in col]
    
    # Define custom weights for each dimension (same as bar chart)
    custom_weights = {
        'Settlement_Index': 0.10,
        'Agriculture_Livestock_Index': 0.12,
        'Housing_Amenities_Index': 0.10,
        'Infrastructure_Services_Index': 0.12,
        'Education_Index': 0.15,
        'Health_Index': 0.15,
        'Recreation_Sports_Index': 0.05,
        'Social_Community_Index': 0.06,
        'Industry_Index': 0.08,
        'Credit_Finance_Index': 0.05,
        'Disaster_Resilience_Index': 0.02
    }
    
    # Calculate custom weighted score
    df_box['Custom_Weighted_Score'] = sum(df_box[col] * custom_weights[col] for col in index_cols)
    
    province_colors = {
        'PUNJAB': '#2e7d32',
        'SINDH': '#ec407a',
        'BALOCHISTAN': '#ff6f00',
        'KHYBER PAKHTUNKHWA': '#795548',
        'AZAD JAMMU AND KASHMIR': '#1976d2',
        'GILGIT BALTISTAN': '#7b1fa2',
        'ISLAMABAD CAPITAL TERRITORY': '#c62828'
    }
    
    # Order provinces alphabetically
    province_order = sorted(df_box['Name of Province'].unique())
    
    # Add spacing before chart
    st.markdown("<div style='margin-bottom: 0.8rem;'></div>", unsafe_allow_html=True)
    
    # Create box plot
    fig = go.Figure()
    
    for province in province_order:
        prov_data = df_box[df_box['Name of Province'] == province]['Custom_Weighted_Score']
        
        fig.add_trace(go.Box(
            y=prov_data,
            name=province,
            marker=dict(
                color=province_colors.get(province, '#95a5a6'),
                opacity=0.7
            ),
            line=dict(color=province_colors.get(province, '#95a5a6'), width=2),
            boxmean='sd',  # Show mean and standard deviation
            hovertemplate=(
                f"<b>{province}</b><br>"
                "Score: %{y:.1f}<br>"
                "<extra></extra>"
            )
        ))
    
    chart_height = 550 if compact else 700
    
    fig.update_layout(
        title=dict(
            text="Distribution of Custom Weighted Scores by Province",
            font=dict(size=14 if not compact else 13, color='#2c3e50', family='Arial, sans-serif', weight='bold'),
            x=0.5,
            xanchor='center',
            y=0.95,
            yanchor='top'
        ),
        xaxis=dict(
            title="",
            tickangle=-45,
            tickfont=dict(size=11)
        ),
        yaxis=dict(
            title=dict(
                text="Custom Weighted Score",
                font=dict(size=12, weight='bold')
            ),
            tickfont=dict(size=10),
            gridcolor='rgba(0, 0, 0, 0.3)',
            showgrid=True
        ),
        height=chart_height,
        margin=dict(l=70, r=40, t=100, b=120),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False
    )
    
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'pakistan_provincial_boxplot',
            'height': 600,
            'width': 1200,
            'scale': 2
        }
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)

# Main content area based on layout mode
if layout_mode == "Concise Dashboard":
    # Add CSS to prevent scrolling
    st.markdown("""
    <style>
        section.main > div {max-height: 100vh; overflow: hidden;}
        .block-container {padding-top: 0.5rem; padding-bottom: 0rem;}
    </style>
    """, unsafe_allow_html=True)
    
    # First row: Map and Radar
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container():
            render_choropleth_map(compact=True)
    
    with col2:
        with st.container():
            render_radar_chart(compact=True)
    
    # Second row: Provincial Bar Chart and Box Plot
    st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        with st.container():
            render_provincial_bar_chart(compact=True)
    
    with col4:
        with st.container():
            render_provincial_boxplot(compact=True)

elif layout_mode == "Vertical Scroll":
    # Add CSS for compact header
    st.markdown("""
    <style>
        .block-container {padding-top: 0.5rem; padding-bottom: 1rem;}
    </style>
    """, unsafe_allow_html=True)
    
    # Traditional vertical layout
    render_choropleth_map(compact=False)
    
    st.markdown("---")
    render_radar_chart(compact=False)
    
    st.markdown("---")
    render_provincial_bar_chart(compact=False)
    
    st.markdown("---")
    render_provincial_boxplot(compact=False)

elif layout_mode == "Multiple Pages":
    # Add CSS to prevent scrolling
    st.markdown("""
    <style>
        section.main > div {max-height: 100vh; overflow: hidden;}
        .block-container {padding-top: 0.5rem; padding-bottom: 0rem;}
    </style>
    """, unsafe_allow_html=True)
    
    # Page navigation controls
    col_nav1, col_nav2, col_nav3 = st.columns([1, 6, 1])
    
    total_pages = 4
    page_titles = ["District Choropleth Map", "Provincial Radar Chart", "Provincial Rankings", "Score Distribution"]
    
    with col_nav1:
        if st.button("◀ Previous", disabled=(st.session_state.current_page == 0)):
            st.session_state.current_page = max(0, st.session_state.current_page - 1)
            st.rerun()
    
    with col_nav2:
        st.markdown(f"""
        <div style='text-align: center; padding: 5px;'>
            <h4 style='margin: 0; color: #2c3e50; font-size: 1.1rem;'>{page_titles[st.session_state.current_page]}</h4>
            <p style='margin: 3px 0 0 0; color: #7f8c8d; font-size: 0.8rem;'>Page {st.session_state.current_page + 1} of {total_pages}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_nav3:
        if st.button("Next ▶", disabled=(st.session_state.current_page >= total_pages - 1)):
            st.session_state.current_page = min(total_pages - 1, st.session_state.current_page + 1)
            st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Display current page
    if st.session_state.current_page == 0:
        render_choropleth_map(compact=False)
    elif st.session_state.current_page == 1:
        render_radar_chart(compact=False)
    elif st.session_state.current_page == 2:
        render_provincial_bar_chart(compact=False)
    elif st.session_state.current_page == 3:
        render_provincial_boxplot(compact=False)

# Footer (shown in all modes)
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; padding: 2rem 0;">
    <p><strong>Pakistan District Development Atlas</strong> | Data Source: Mouza Census 2020 | 
    Coverage: 97.2% (138/142 districts)</p>
    <p>Developed using Streamlit, Folium, and GeoPandas | 
    Last Updated: December 11, 2025</p>
</div>
""", unsafe_allow_html=True)
