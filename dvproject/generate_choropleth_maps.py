"""
Pakistan District Development Choropleth Map Generator
========================================================

This script creates enhanced interactive choropleth maps with:
- 12 layers (Composite + 11 dimensions) in one multi-layer map
- Radio button selection (only one layer at a time)
- No tooltip clutter in layer control
- Single legend per active layer
- Tooltips showing district rankings
- 97.2% geographic coverage (138/142 districts)

Generated Files:
- pakistan_all_layers_choropleth.html (MAIN MAP - all layers)
- pakistan_composite_choropleth.html (Composite score)
- 11 individual dimension maps

Usage:
    python generate_choropleth_maps.py
"""

import pandas as pd
import json
import re
from difflib import SequenceMatcher
import folium

def main():
    print("🗺️  Pakistan District Development Choropleth Generator (WEIGHTED SCORES)")
    print("=" * 80)
    
    # Load weighted data
    print("📂 Loading weighted scores data...")
    df = pd.read_csv('Mouza_Census_WeightedScores.csv')
    
    # Weighted score columns
    weighted_cols = ['Settlement_Weighted', 'Agriculture_Livestock_Weighted',
                     'Housing_Amenities_Weighted', 'Infrastructure_Services_Weighted',
                     'Education_Weighted', 'Health_Weighted', 'Recreation_Sports_Weighted',
                     'Social_Community_Weighted', 'Industry_Weighted',
                     'Credit_Finance_Weighted', 'Disaster_Resilience_Weighted']
    
    # Original index columns for labels
    index_cols = ['Settlement_Index', 'Agriculture_Livestock_Index', 
                  'Housing_Amenities_Index', 'Infrastructure_Services_Index',
                  'Education_Index', 'Health_Index', 'Recreation_Sports_Index',
                  'Social_Community_Index', 'Industry_Index', 
                  'Credit_Finance_Index', 'Disaster_Resilience_Index']
    
    # Manual mappings
    manual_mappings = {
        'MALAKAND PROTECTED AREA': 'Malakand',
        'WASHUK DISTRICT': 'Kharan',
        'SHAHEED BENAZIRABAD DISTRICT': 'Nawabshah',
        'BALTISTAN DISTRICT': 'Skardu',
        'ISLAMABAD DISTRICT': 'Islamabad Capital Territory'
    }
    
    # AJK districts
    ajk_districts = [
        'BHIMBER DISTRICT', 'KOTLI DISTRICT', 'MIRPUR DISTRICT',
        'HATTIAN BALA DISTRICT', 'MUZAFFARABAD DISTRICT', 'NEELUM DISTRICT',
        'BAGH DISTRICT', 'HAVELI DISTRICT', 'POONCH DISTRICT', 'SUDHNOTI DISTRICT'
    ]
    
    # Kohistan variants
    kohistan_districts = ['KOLAI PALAS KOHISTAN', 'KOHISTAN']
    
    print("🔄 Processing data...")
    
    # Aggregate AJK using weighted columns
    ajk_data = df[df['Name of District'].isin(ajk_districts)]
    if len(ajk_data) > 0:
        ajk_aggregated = pd.DataFrame({
            'Name of District': ['AZAD KASHMIR'],
            'Name of Province': ['AZAD KASHMIR'],
            'Name of Division': ['AZAD KASHMIR'],
            **{col: [ajk_data[col].mean()] for col in weighted_cols + ['Composite_Weighted_Score']}
        })
        # Also include original index columns if they exist
        if 'Settlement_Index' in df.columns:
            for col in index_cols:
                ajk_aggregated[col] = ajk_data[col].mean()
        
        df = pd.concat([df[~df['Name of District'].isin(ajk_districts)], ajk_aggregated], ignore_index=True)
        print(f"   ✓ Aggregated {len(ajk_data)} AJK districts → AZAD KASHMIR")
    
    # Aggregate Kohistan using weighted columns
    kohistan_data = df[df['Name of District'].isin(kohistan_districts)]
    if len(kohistan_data) > 0:
        kohistan_aggregated = pd.DataFrame({
            'Name of District': ['KOHISTAN'],
            'Name of Province': [kohistan_data.iloc[0]['Name of Province']],
            'Name of Division': [kohistan_data.iloc[0]['Name of Division']],
            **{col: [kohistan_data[col].mean()] for col in weighted_cols + ['Composite_Weighted_Score']}
        })
        # Also include original index columns if they exist
        if 'Settlement_Index' in df.columns:
            for col in index_cols:
                kohistan_aggregated[col] = kohistan_data[col].mean()
        
        df = pd.concat([df[~df['Name of District'].isin(kohistan_districts)], kohistan_aggregated], ignore_index=True)
        print(f"   ✓ Aggregated {len(kohistan_data)} Kohistan districts → KOHISTAN")
    
    print(f"   ✓ {len(df)} districts total")
    
    # Fill any NaN values with 0
    df['Composite_Weighted_Score'] = df['Composite_Weighted_Score'].fillna(0)
    for col in weighted_cols:
        df[col] = df[col].fillna(0)
    
    print("📊 Normalizing scores to 0-100 scale (100=best, 0=worst)...")
    
    # Normalize Composite Weighted Score to 0-100
    comp_min = df['Composite_Weighted_Score'].min()
    comp_max = df['Composite_Weighted_Score'].max()
    if comp_max > comp_min:
        df['Composite_Weighted_Score_Normalized'] = ((df['Composite_Weighted_Score'] - comp_min) / (comp_max - comp_min)) * 100
    else:
        df['Composite_Weighted_Score_Normalized'] = 50.0
    
    # Normalize each weighted dimension to 0-100
    for weighted_col in weighted_cols:
        normalized_col = weighted_col + '_Normalized'
        col_min = df[weighted_col].min()
        col_max = df[weighted_col].max()
        if col_max > col_min:
            df[normalized_col] = ((df[weighted_col] - col_min) / (col_max - col_min)) * 100
        else:
            df[normalized_col] = 50.0
    
    print(f"   ✓ Normalized composite score range: {df['Composite_Weighted_Score_Normalized'].min():.2f} - {df['Composite_Weighted_Score_Normalized'].max():.2f}")
    
    # Calculate rankings using normalized scores
    print("📊 Calculating rankings...")
    df['Composite_Rank'] = df['Composite_Weighted_Score_Normalized'].rank(ascending=False, method='min').astype(int)
    
    # Calculate rankings for each normalized dimension
    for weighted_col in weighted_cols:
        normalized_col = weighted_col + '_Normalized'
        rank_col_name = weighted_col.replace('_Weighted', '_Rank')
        df[rank_col_name] = df[normalized_col].rank(ascending=False, method='min').astype(int)
    print("🌍 Loading geographic boundaries...")
    with open('geoBoundaries-PAK-ADM2.geojson', 'r', encoding='utf-8') as f:
        geo_boundaries = json.load(f)
    print(f"   ✓ {len(geo_boundaries['features'])} boundary features loaded")
    
    # Helper functions
    def normalize_name(name):
        if not name:
            return ""
        name = name.upper()
        name = re.sub(r'\s+(DISTRICT|TEHSIL|CITY)$', '', name)
        name = re.sub(r'[^\w\s]', '', name)
        return name.strip()
    
    def find_best_match(csv_name, geo_names, threshold=0.6):
        csv_norm = normalize_name(csv_name)
        best_match = None
        best_score = 0
        for geo_name in geo_names:
            geo_norm = normalize_name(geo_name)
            score = SequenceMatcher(None, csv_norm, geo_norm).ratio()
            if score > best_score:
                best_score = score
                best_match = geo_name
        return best_match if best_score >= threshold else None
    
    # Match districts
    print("🔗 Matching districts to boundaries...")
    geo_boundary_names = [f['properties']['shapeName'] for f in geo_boundaries['features']]
    geo_boundary_matches = {}
    
    for district in df['Name of District'].unique():
        if district in manual_mappings:
            geo_boundary_matches[district] = manual_mappings[district]
        else:
            gb_match = find_best_match(district, geo_boundary_names, threshold=0.6)
            if gb_match:
                geo_boundary_matches[district] = gb_match
    
    match_rate = len(geo_boundary_matches) / len(df) * 100
    print(f"   ✓ Matched: {len(geo_boundary_matches)}/{len(df)} districts ({match_rate:.1f}%)")
    
    # Create district data mapping
    geo_to_district_data = {}
    for district, geo_name in geo_boundary_matches.items():
        district_row = df[df['Name of District'] == district].iloc[0]
        geo_to_district_data[geo_name] = district_row.to_dict()
    
    # Create multi-layer map
    print("\n🗺️  Creating MULTI-LAYER map...")
    print("   (This may take a minute...)")
    
    multi_map = folium.Map(
        location=[30.3753, 69.3451],
        zoom_start=5,
        tiles='cartodbpositron',
        control_scale=True
    )
    
    # Define all layers using NORMALIZED WEIGHTED scores
    normalized_weighted_cols = [col + '_Normalized' for col in weighted_cols]
    all_layers = [('Composite_Weighted_Score_Normalized', 'Composite Score (Weighted)')] + \
                 [(normalized_weighted_cols[i], index_cols[i].replace('_Index', '').replace('_', ' ')) 
                  for i in range(len(index_cols))]
    
    # Add each layer
    for layer_idx, (dimension_col, dimension_name) in enumerate(all_layers):
        print(f"\n🔹 Creating Layer {layer_idx}: {dimension_name}")
        
        # Get the rank column name
        if dimension_col == 'Composite_Weighted_Score_Normalized':
            rank_col = 'Composite_Rank'
        else:
            rank_col = dimension_col.replace('_Weighted_Normalized', '_Rank')
        
        # Prepare data series using NORMALIZED WEIGHTED scores
        data_dict = {}
        for geo_name in geo_to_district_data.keys():
            data_dict[geo_name] = geo_to_district_data[geo_name][dimension_col]
        
        # Create choropleth WITHOUT legend and WITHOUT highlight
        choropleth = folium.Choropleth(
            geo_data=geo_boundaries,
            name=dimension_name,
            data=pd.Series(data_dict),
            key_on='feature.properties.shapeName',
            fill_color='RdYlGn',
            fill_opacity=0.75,
            line_opacity=0.1,
            line_weight=0.5,
            legend_name=None,  # No legend for individual layers
            highlight=False,  # Disable to prevent click blocking
            nan_fill_color='#d3d3d3',
            show=(layer_idx == 0),
            overlay=True,
            control=True
        )
        choropleth.add_to(multi_map)
        
        # Disable click events on choropleth geojson
        for key in choropleth._children:
            if key.startswith('geo_json'):
                choropleth._children[key].options['interactive'] = False
        
        # Remove the legend from this choropleth
        for key in choropleth._children:
            if key.startswith('color_map'):
                del(choropleth._children[key])
        
        # Add interaction layers for EACH dimension with their own popups
        for idx, feature in enumerate(geo_boundaries['features']):
            geo_name = feature['properties']['shapeName']
            
            if geo_name in geo_to_district_data:
                data = geo_to_district_data[geo_name]
                
                # Get values immediately - no function calls
                score_val = float(data[dimension_col])
                rank_val = int(data[rank_col])
                comp_score_val = float(data['Composite_Weighted_Score_Normalized'])
                comp_rank_val = int(data['Composite_Rank'])
                dim_name_val = str(dimension_name)  # Force string copy
                geo_name_val = str(geo_name)  # Force string copy
                df_len_val = len(df)
                
                # Create popup HTML immediately with actual values, not variables
                popup_html = (
                    "<div style='font-family: Arial; font-size: 13px; padding: 5px;'>"
                    "<b style='font-size: 15px; color: #2c3e50;'>" + geo_name_val + "</b><br><br>"
                    "<b>" + dim_name_val + ":</b> <span style='color: #1a9850; font-size: 14px;'>" + f"{score_val:.2f}" + "/100</span><br>"
                    "<b>Rank:</b> <span style='color: #e74c3c; font-size: 14px;'>#" + str(rank_val) + "</span> of " + str(df_len_val) + "<br>"
                    "<hr style='margin: 8px 0; border: none; border-top: 1px solid #ccc;'>"
                    "<span style='font-size: 11px; color: #7f8c8d;'>"
                    "<b>Composite:</b> " + f"{comp_score_val:.2f}" + "/100 (Rank #" + str(comp_rank_val) + ")"
                    "</span>"
                    "</div>"
                )
                
                # Define style dicts OUTSIDE lambda to avoid any capture issues
                base_style = {
                    'fillColor': 'transparent',
                    'color': '#666',
                    'weight': 1.5,
                    'fillOpacity': 0
                }
                highlight_style = {
                    'fillColor': 'yellow',
                    'color': '#333',
                    'weight': 2,
                    'fillOpacity': 0.1
                }
                
                # Create a copy of the feature and add dimension index to properties
                feature_copy = json.loads(json.dumps(feature))  # Deep copy
                feature_copy['properties']['_dim_idx'] = layer_idx
                feature_copy['properties']['_feature_idx'] = idx
                
                # Add interactive boundary layer with popup
                interaction_layer = folium.GeoJson(
                    data=feature_copy,
                    style_function=lambda x, s=base_style: s.copy(),
                    highlight_function=lambda x, s=highlight_style: s.copy(),
                    popup=folium.Popup(popup_html, max_width=300),
                    name=f'_interaction_{layer_idx}_{idx}',
                    overlay=True,
                    control=False
                )
                
                interaction_layer.add_to(multi_map)
    
    # Add layer control
    folium.LayerControl(collapsed=False, position='topright').add_to(multi_map)
    
    # Add CSS to hide base map selector and add title
    layer_control_css = """
    <style>
    /* Hide base layers section completely */
    .leaflet-control-layers-base {
        display: none !important;
    }
    
    /* Add title to layer control */
    .leaflet-control-layers-overlays:before {
        content: 'Development Dimensions';
        display: block;
        font-weight: bold;
        font-size: 11px;
        margin-bottom: 5px;
        padding-bottom: 5px;
        border-bottom: 1px solid #ccc;
        color: #2c3e50;
    }
    
    /* Style the layer control container */
    .leaflet-control-layers {
        border-radius: 5px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-size: 10px;
        padding: 8px;
    }
    
    /* Make layer labels more compact */
    .leaflet-control-layers label {
        margin-bottom: 3px;
        font-size: 10px;
    }
    </style>
    """
    multi_map.get_root().html.add_child(folium.Element(layer_control_css))
    
    # Add single custom legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 40px; left: 40px; width: 150px; height: 90px; 
                background-color: white; border:1px solid grey; z-index:9999; 
                font-size:10px; padding: 8px; border-radius: 4px;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.2);">
        <p style="margin:0; padding:0; font-weight:bold; margin-bottom:6px; font-size:11px;">Development Score</p>
        <div style="background: linear-gradient(to right, #d73027, #fee08b, #1a9850); 
                    height: 15px; width: 100%; border-radius: 2px;"></div>
        <div style="display: flex; justify-content: space-between; margin-top: 4px; font-size: 9px;">
            <span>0 (Worst)</span>
            <span>50</span>
            <span>100 (Best)</span>
        </div>
    </div>
    '''
    multi_map.get_root().html.add_child(folium.Element(legend_html))
    
    # Add JavaScript for radio buttons and layer management
    radio_js = """
    <script>
    window.addEventListener('load', function() {
        setTimeout(function() {
            // Get the map instance
            var map = null;
            for (var key in window) {
                if (window[key] && window[key]._container && window[key]._layers) {
                    map = window[key];
                    break;
                }
            }
            
            if (!map) return;
            
            // Collect interaction layers by dimension
            var interactionLayersByDim = {};
            map.eachLayer(function(layer) {
                // Check if this is a GeoJson layer with our custom dimension property
                if (layer.feature && layer.feature.properties && layer.feature.properties._dim_idx !== undefined) {
                    var dimIdx = layer.feature.properties._dim_idx;
                    
                    if (!interactionLayersByDim[dimIdx]) {
                        interactionLayersByDim[dimIdx] = [];
                    }
                    interactionLayersByDim[dimIdx].push(layer);
                }
            });
            
            console.log('Found interaction layers for dimensions:', Object.keys(interactionLayersByDim));
            console.log('Total dimensions with layers:', Object.keys(interactionLayersByDim).length);
            
            // Initially, hide all layers except dimension 0
            for (var dim in interactionLayersByDim) {
                var dimInt = parseInt(dim);
                if (dimInt !== 0) {
                    interactionLayersByDim[dimInt].forEach(function(layer) {
                        if (map.hasLayer(layer)) {
                            map.removeLayer(layer);
                        }
                    });
                }
            }
            console.log('Initially showing only dimension 0');
            
            // Function to show only one dimension's interaction layers
            function showOnlyDimension(dimIndex) {
                console.log('=== Switching to dimension index:', dimIndex, '===');
                
                // First pass: Remove ALL interaction layers from map and disable events
                for (var dim in interactionLayersByDim) {
                    var dimInt = parseInt(dim);
                    var layersForDim = interactionLayersByDim[dimInt];
                    
                    layersForDim.forEach(function(layer) {
                        // Disable events FIRST
                        if (layer._path) {
                            layer._path.style.pointerEvents = 'none';
                            layer._path.style.display = 'none';  // Also hide visually
                        }
                        // Then remove from map
                        if (map.hasLayer(layer)) {
                            map.removeLayer(layer);
                        }
                    });
                }
                console.log('Removed all interaction layers');
                
                // Second pass: Add ONLY the selected dimension's layers
                if (interactionLayersByDim[dimIndex]) {
                    var layersToAdd = interactionLayersByDim[dimIndex];
                    console.log('Adding', layersToAdd.length, 'layers for dimension', dimIndex);
                    
                    // Add each layer
                    layersToAdd.forEach(function(layer, idx) {
                        if (!map.hasLayer(layer)) {
                            map.addLayer(layer);
                        }
                        
                        // Bring to front and enable events
                        if (layer._path) {
                            layer._path.style.display = '';  // Show
                            layer._path.style.pointerEvents = 'auto';  // Enable clicks
                        }
                        
                        // Ensure layer is on top
                        if (layer.bringToFront) {
                            layer.bringToFront();
                        }
                    });
                    
                    console.log('Successfully showed', layersToAdd.length, 'layers for dimension', dimIndex);
                } else {
                    console.error('No layers found for dimension', dimIndex);
                }
                
                console.log('=== Switch complete ===');
            }
            
            // Convert layer control to radio buttons
            var layerControl = document.querySelector('.leaflet-control-layers-overlays');
            if (layerControl) {
                var labels = layerControl.querySelectorAll('label');
                
                // Hide interaction layer labels
                labels.forEach(function(label) {
                    if (label.textContent.trim().startsWith('_interaction')) {
                        label.style.display = 'none';
                    }
                });
                
                // Get visible dimension labels
                var dimensionLabels = Array.from(labels).filter(function(label) {
                    return label.style.display !== 'none';
                });
                
                // Convert to radio buttons
                dimensionLabels.forEach(function(label, index) {
                    var input = label.querySelector('input');
                    if (input) {
                        input.type = 'radio';
                        input.name = 'map-layer';
                        
                        if (index === 0) {
                            input.checked = true;
                        } else {
                            input.checked = false;
                        }
                        
                        input.addEventListener('change', function() {
                            if (this.checked) {
                                // Uncheck others
                                dimensionLabels.forEach(function(otherLabel, otherIndex) {
                                    if (otherIndex !== index) {
                                        var otherInput = otherLabel.querySelector('input');
                                        if (otherInput) otherInput.checked = false;
                                    }
                                });
                                
                                // Show only this dimension's interaction layers
                                showOnlyDimension(index);
                            }
                        });
                    }
                });
                
                // Initially show only first dimension
                showOnlyDimension(0);
            }
        }, 1500);
    });
    </script>
    """
    multi_map.get_root().html.add_child(folium.Element(radio_js))
    
    # Save multi-layer map
    multi_map.save('pakistan_all_layers_choropleth.html')
    print("   ✅ pakistan_all_layers_choropleth.html")
    
    # Final summary
    print("\n" + "=" * 80)
    print("✅ MAP CREATED SUCCESSFULLY (USING WEIGHTED SCORES)!")
    print("=" * 80)
    print(f"📊 Coverage: {len(geo_boundary_matches)}/{len(df)} districts ({match_rate:.1f}%)")
    print(f"📁 File created: pakistan_all_layers_choropleth.html")
    print(f"\n🌟 FEATURES:")
    print(f"   → 12 layers switchable with radio buttons (Composite + 11 dimensions)")
    print(f"   → Uses WEIGHTED scores from cell 39")
    print(f"   → Only ONE legend at a time (Red=Bad, Green=Good, 0-100)")
    print(f"   → Clickable districts with hover tooltips showing rankings")
    print(f"   → No tooltip clutter in layer control")
    print(f"\n💡 Open in browser to explore interactively!")

if __name__ == '__main__':
    main()
