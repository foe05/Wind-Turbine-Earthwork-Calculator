-- =============================================================================
-- Demo Data for Geo-Engineering Platform
-- Phase 1 + Phase 2
-- =============================================================================

-- Get demo user IDs
DO $$
DECLARE
    demo_user_id UUID;
    test_user_id UUID;
BEGIN
    -- Get user IDs
    SELECT id INTO demo_user_id FROM users WHERE email = 'demo@geo-engineering.de';
    SELECT id INTO test_user_id FROM users WHERE email = 'test@example.com';

    -- =============================================================================
    -- DEMO PROJECTS
    -- =============================================================================

    -- WKA Project (Wind Farm Brandenburg)
    INSERT INTO projects (id, user_id, use_case, name, description, crs, utm_zone, bounds, metadata)
    VALUES (
        '11111111-1111-1111-1111-111111111111'::uuid,
        demo_user_id,
        'wka',
        'Windpark Brandenburg - Prignitz',
        'Windenergieprojekt mit 5 Standorten in Brandenburg, 6 MW Anlagen',
        'EPSG:25833',
        33,
        ST_GeomFromText('POLYGON((13.0 53.0, 13.2 53.0, 13.2 53.2, 13.0 53.2, 13.0 53.0))', 4326),
        jsonb_build_object(
            'turbine_type', 'Vestas V162-6.2',
            'hub_height', 169,
            'rotor_diameter', 162,
            'rated_power', 6200,
            'expected_annual_production', '95 GWh'
        )
    );

    -- Road Project (L135 Modernisierung)
    INSERT INTO projects (id, user_id, use_case, name, description, crs, utm_zone, bounds, metadata)
    VALUES (
        '22222222-2222-2222-2222-222222222222'::uuid,
        demo_user_id,
        'road',
        'L135 Modernisierung - Uckermark',
        'Straßenausbau L135 zwischen Prenzlau und Templin, 8.5 km',
        'EPSG:25833',
        33,
        ST_GeomFromText('POLYGON((13.5 53.2, 13.7 53.2, 13.7 53.4, 13.5 53.4, 13.5 53.2))', 4326),
        jsonb_build_object(
            'road_type', 'Landesstraße',
            'road_class', 'L135',
            'design_speed', '100 km/h',
            'lane_count', 2,
            'pavement_type', 'Asphalt'
        )
    );

    -- Solar Project (Solarpark Lausitz)
    INSERT INTO projects (id, user_id, use_case, name, description, crs, utm_zone, bounds, metadata)
    VALUES (
        '33333333-3333-3333-3333-333333333333'::uuid,
        demo_user_id,
        'solar',
        'Solarpark Lausitz - Cottbus Süd',
        'Freiflächen-PV-Anlage 50 MWp auf ehemaliger Tagebaufläche',
        'EPSG:25833',
        33,
        ST_GeomFromText('POLYGON((14.2 51.6, 14.5 51.6, 14.5 51.8, 14.2 51.8, 14.2 51.6))', 4326),
        jsonb_build_object(
            'peak_power', '50 MWp',
            'panel_type', 'Bifazial N-Type 580W',
            'module_count', 86207,
            'expected_annual_yield', '55 GWh',
            'land_area', '60 ha'
        )
    );

    -- Terrain Analysis Project (Bergbau-Renaturierung)
    INSERT INTO projects (id, user_id, use_case, name, description, crs, utm_zone, bounds, metadata)
    VALUES (
        '44444444-4444-4444-4444-444444444444'::uuid,
        demo_user_id,
        'terrain',
        'Tagebau Jänschwalde - Renaturierung Phase 1',
        'Geländeanalyse für Rekultivierung ehemaliger Tagebaufläche',
        'EPSG:25833',
        33,
        ST_GeomFromText('POLYGON((14.4 51.8, 14.6 51.8, 14.6 52.0, 14.4 52.0, 14.4 51.8))', 4326),
        jsonb_build_object(
            'area_type', 'Ehemalige Tagebaufläche',
            'reclamation_goal', 'Mischwald mit Naherholungsgebiet',
            'analysis_purpose', 'Erdmassenbilanz und Geländemodellierung'
        )
    );

    -- =============================================================================
    -- DEMO JOBS (Completed calculations)
    -- =============================================================================

    -- WKA Job 1: Completed calculation for Site 1
    INSERT INTO jobs (
        id, project_id, status, progress,
        started_at, completed_at,
        input_data, result_data, site_count
    )
    VALUES (
        '11111111-aaaa-1111-aaaa-111111111111'::uuid,
        '11111111-1111-1111-1111-111111111111'::uuid,
        'completed',
        100,
        NOW() - INTERVAL '2 hours',
        NOW() - INTERVAL '1 hour 50 minutes',
        jsonb_build_object(
            'center_x', 402500,
            'center_y', 5885000,
            'foundation_diameter', 25.0,
            'foundation_depth', 4.0,
            'platform_length', 45.0,
            'platform_width', 45.0,
            'optimization_method', 'balanced'
        ),
        jsonb_build_object(
            'foundation_volume', 1963.5,
            'platform_height', 87.35,
            'total_cut', 8234.2,
            'total_fill', 8156.8,
            'total_cost', 245680.50
        ),
        1
    );

    -- Road Job 1: Completed road calculation
    INSERT INTO jobs (
        id, project_id, status, progress,
        started_at, completed_at,
        input_data, result_data
    )
    VALUES (
        '22222222-bbbb-2222-bbbb-222222222222'::uuid,
        '22222222-2222-2222-2222-222222222222'::uuid,
        'completed',
        100,
        NOW() - INTERVAL '3 hours',
        NOW() - INTERVAL '2 hours 45 minutes',
        jsonb_build_object(
            'centerline', '[[408000,5920000],[408500,5920200],[409000,5920500]]',
            'road_width', 7.5,
            'design_grade', 2.5,
            'profile_type', 'crowned',
            'station_interval', 25.0
        ),
        jsonb_build_object(
            'road_length', 8523.4,
            'total_cut', 45678.3,
            'total_fill', 42341.2,
            'net_volume', 3337.1,
            'num_stations', 342
        )
    );

    -- Solar Job 1: Completed solar park calculation
    INSERT INTO jobs (
        id, project_id, status, progress,
        started_at, completed_at,
        input_data, result_data
    )
    VALUES (
        '33333333-cccc-3333-cccc-333333333333'::uuid,
        '33333333-3333-3333-3333-333333333333'::uuid,
        'completed',
        100,
        NOW() - INTERVAL '4 hours',
        NOW() - INTERVAL '3 hours 40 minutes',
        jsonb_build_object(
            'boundary', '[[415000,5710000],[415800,5710000],[415800,5710600],[415000,5710600]]',
            'panel_length', 2.3,
            'panel_width', 1.3,
            'row_spacing', 5.5,
            'panel_tilt', 25.0,
            'foundation_type', 'ramming',
            'grading_strategy', 'minimal'
        ),
        jsonb_build_object(
            'num_panels', 86207,
            'panel_area', 257821.0,
            'site_area', 600000.0,
            'total_cut', 12456.8,
            'total_fill', 11234.5,
            'foundation_volume', 4321.2
        )
    );

    -- Terrain Job 1: Cut/Fill balance analysis
    INSERT INTO jobs (
        id, project_id, status, progress,
        started_at, completed_at,
        input_data, result_data
    )
    VALUES (
        '44444444-dddd-4444-dddd-444444444444'::uuid,
        '44444444-4444-4444-4444-444444444444'::uuid,
        'completed',
        100,
        NOW() - INTERVAL '1 hour',
        NOW() - INTERVAL '50 minutes',
        jsonb_build_object(
            'polygon', '[[418000,5750000],[418500,5750000],[418500,5750500],[418000,5750500]]',
            'analysis_type', 'cut_fill_balance',
            'resolution', 2.0,
            'optimization_method', 'balanced'
        ),
        jsonb_build_object(
            'polygon_area', 250000.0,
            'optimal_elevation', 125.34,
            'cut_volume', 89456.3,
            'fill_volume', 89123.7,
            'net_volume', 332.6,
            'avg_elevation', 125.45,
            'min_elevation', 118.2,
            'max_elevation', 132.8
        )
    );

    -- Terrain Job 2: Slope analysis
    INSERT INTO jobs (
        id, project_id, status, progress,
        started_at, completed_at,
        input_data, result_data
    )
    VALUES (
        '44444444-eeee-4444-eeee-444444444444'::uuid,
        '44444444-4444-4444-4444-444444444444'::uuid,
        'completed',
        100,
        NOW() - INTERVAL '40 minutes',
        NOW() - INTERVAL '35 minutes',
        jsonb_build_object(
            'polygon', '[[418200,5750200],[418400,5750200],[418400,5750400],[418200,5750400]]',
            'analysis_type', 'slope_analysis',
            'resolution', 1.0
        ),
        jsonb_build_object(
            'polygon_area', 40000.0,
            'avg_slope', 4.2,
            'min_slope', 0.5,
            'max_slope', 12.8,
            'median_slope', 3.8,
            'slope_percentile_90', 8.5
        )
    );

    -- =============================================================================
    -- CALCULATION RESULTS (Sample site results for WKA)
    -- =============================================================================

    INSERT INTO calculation_results (
        id, job_id, site_id,
        point_geometry,
        foundation_volume, cut_volume, fill_volume, net_volume,
        ground_elevation, platform_height, optimization_method,
        total_cost, cost_breakdown
    )
    VALUES (
        '11111111-res1-1111-res1-111111111111'::uuid,
        '11111111-aaaa-1111-aaaa-111111111111'::uuid,
        1,
        ST_SetSRID(ST_MakePoint(13.1, 53.1), 4326),
        1963.5,
        8234.2,
        8156.8,
        77.4,
        87.35,
        45.0,
        'balanced',
        245680.50,
        jsonb_build_object(
            'excavation', 98523.40,
            'fill_material', 122458.20,
            'platform_prep', 24699.00
        )
    );

    -- =============================================================================
    -- REPORTS (Sample generated reports)
    -- =============================================================================

    INSERT INTO reports (
        id, job_id, format,
        file_path, file_size, download_url,
        generated_at, expires_at
    )
    VALUES
    (
        'rep11111-1111-1111-1111-111111111111'::uuid,
        '11111111-aaaa-1111-aaaa-111111111111'::uuid,
        'pdf',
        '/app/reports/report_rep11111-1111-1111-1111-111111111111.pdf',
        524288,
        '/report/download/rep11111-1111-1111-1111-111111111111/report_rep11111-1111-1111-1111-111111111111.pdf',
        NOW() - INTERVAL '1 hour',
        NOW() + INTERVAL '29 days'
    ),
    (
        'rep22222-2222-2222-2222-222222222222'::uuid,
        '22222222-bbbb-2222-bbbb-222222222222'::uuid,
        'html',
        '/app/reports/report_rep22222-2222-2222-2222-222222222222.html',
        156789,
        '/report/download/rep22222-2222-2222-2222-222222222222/report_rep22222-2222-2222-2222-222222222222.html',
        NOW() - INTERVAL '2 hours',
        NOW() + INTERVAL '28 days'
    );

    -- =============================================================================
    -- REPORT TEMPLATES (Base templates for all use cases)
    -- =============================================================================

    INSERT INTO report_templates (id, name, type, description, html_template, css_template, default_variables, available_sections, created_by)
    VALUES
    (
        'tpl-wka-standard'::uuid,
        'Standard WKA Report',
        'wka',
        'Standardbericht für Windkraftanlagen-Erdarbeiten',
        '<html><!-- WKA Template --></html>',
        'body { font-family: Arial; }',
        '{"header_color": "#2C3E50", "accent_color": "#E74C3C"}'::jsonb,
        '["overview", "sites", "volumes", "costs", "material_balance"]'::jsonb,
        demo_user_id
    ),
    (
        'tpl-road-standard'::uuid,
        'Standard Road Report',
        'road',
        'Standardbericht für Straßenbau-Erdarbeiten',
        '<html><!-- Road Template --></html>',
        'body { font-family: Arial; }',
        '{"header_color": "#34495E", "accent_color": "#E67E22"}'::jsonb,
        '["overview", "parameters", "stations", "profile", "costs"]'::jsonb,
        demo_user_id
    ),
    (
        'tpl-solar-standard'::uuid,
        'Standard Solar Report',
        'solar',
        'Standardbericht für Solarpark-Erdarbeiten',
        '<html><!-- Solar Template --></html>',
        'body { font-family: Arial; }',
        '{"header_color": "#F39C12", "accent_color": "#E67E22"}'::jsonb,
        '["overview", "layout", "earthwork", "foundations", "costs"]'::jsonb,
        demo_user_id
    ),
    (
        'tpl-terrain-standard'::uuid,
        'Standard Terrain Report',
        'terrain',
        'Standardbericht für Geländeanalysen',
        '<html><!-- Terrain Template --></html>',
        'body { font-family: Arial; }',
        '{"header_color": "#16A085", "accent_color": "#E67E22"}'::jsonb,
        '["overview", "analysis", "statistics", "slopes", "contours"]'::jsonb,
        demo_user_id
    );

    -- =============================================================================
    -- USER TEMPLATE OVERRIDES (Demo customizations)
    -- =============================================================================

    INSERT INTO user_template_overrides (
        id, user_id, template_id,
        logo_url, company_name, company_address, company_email, company_phone,
        color_scheme, enabled_sections, custom_text_blocks, custom_fields
    )
    VALUES
    (
        'override-demo-wka'::uuid,
        demo_user_id,
        'tpl-wka-standard'::uuid,
        'https://example.com/logo.png',
        'GeoEngineering Solutions GmbH',
        'Musterstraße 123, 10115 Berlin',
        'kontakt@geoengineering.example.de',
        '+49 30 12345678',
        'blue',
        '["overview", "sites", "volumes", "costs"]'::jsonb,
        '[{"position": "after_overview", "title": "Projekthinweis", "text": "Alle Berechnungen basieren auf DGM1 Daten von hoehendaten.de"}]'::jsonb,
        '{"project_number": "WKA-2024-001", "order_number": "AUF-2024-042"}'::jsonb
    );

END $$;
