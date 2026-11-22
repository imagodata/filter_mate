<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis autoRefreshMode="Disabled" autoRefreshTime="0" hasScaleBasedVisibilityFlag="0" labelsEnabled="0" layerType="Vector" maxScale="0" minScale="100000000" simplifyAlgorithm="0" simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyLocal="1" simplifyMaxScale="1" styleCategories="Symbology|Labeling|Rendering" symbologyReferenceScale="-1" version="4.3.0-Master">
 <renderer-v2 enableorderby="0" forceraster="0" referencescale="-1" symbollevels="1" type="RuleRenderer">
  <rules key="{9bbe0ceb-50f8-42b2-811c-e9548262d1cc}">
   <rule filter="&quot;waterway&quot; IS 'river'" key="{4d8c8709-8a04-4282-a240-6782fd8fbd9e}" label="waterways:water-river" symbol="0"/>
   <rule filter="&quot;waterway&quot; IS 'canal'" key="{9bb65324-7934-4452-9d6f-1851e60d55b7}" label="waterways:water-canal" symbol="1"/>
   <rule filter="&quot;waterway&quot; IS 'stream'" key="{ad3494e8-dc24-4cf1-83cc-1c6b73c2a6c5}" label="waterways:water-stream" symbol="2"/>
   <rule filter="&quot;waterway&quot; IS 'ditch'" key="{0227d8da-f5b6-44e0-95e8-e85bf4ea8086}" label="waterways:water-ditch" symbol="3"/>
  </rules>
  <symbols>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="0" type="line">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleLine" enabled="1" id="{23ceeddc-857d-45c8-aa29-82f5f6ce784b}" locked="0" pass="0">
     <Option type="Map">
      <Option name="align_dash_pattern" type="QString" value="0"/>
      <Option name="capstyle" type="QString" value="round"/>
      <Option name="customdash" type="QString" value="5;2"/>
      <Option name="customdash_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="customdash_unit" type="QString" value="MM"/>
      <Option name="dash_pattern_offset" type="QString" value="0"/>
      <Option name="dash_pattern_offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="dash_pattern_offset_unit" type="QString" value="MM"/>
      <Option name="draw_inside_polygon" type="QString" value="0"/>
      <Option name="joinstyle" type="QString" value="round"/>
      <Option name="line_color" type="QString" value="190,221,243,255,rgb:0.7450981,0.8666667,0.9529412,1"/>
      <Option name="line_style" type="QString" value="solid"/>
      <Option name="line_width" type="QString" value="0"/>
      <Option name="line_width_unit" type="QString" value="MM"/>
      <Option name="offset" type="QString" value="0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="ring_filter" type="QString" value="0"/>
      <Option name="trim_distance_end" type="QString" value="0"/>
      <Option name="trim_distance_end_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="trim_distance_end_unit" type="QString" value="MM"/>
      <Option name="trim_distance_start" type="QString" value="0"/>
      <Option name="trim_distance_start_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="trim_distance_start_unit" type="QString" value="MM"/>
      <Option name="tweak_dash_pattern_on_corners" type="QString" value="0"/>
      <Option name="use_custom_dash" type="QString" value="0"/>
      <Option name="width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties" type="Map">
        <Option name="enabled" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="(CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 9 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),9,10,0,3)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 15 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),10,15,3,5)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 15 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 17 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),15,17,5,9)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 17 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 18 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),17,18,9,20)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 18 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 20 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),18,20,20,60)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 20 THEN 15.875 END) > 0"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineWidth" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 9 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),9,10,0,3)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 15 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),10,15,3,5)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 15 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 17 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),15,17,5,9)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 17 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 18 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),17,18,9,20)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 18 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 20 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),18,20,20,60)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 20 THEN 15.875 END"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="1" type="line">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleLine" enabled="1" id="{5b6a7cd5-c99f-46ab-935b-e3352bb6a5af}" locked="0" pass="1">
     <Option type="Map">
      <Option name="align_dash_pattern" type="QString" value="0"/>
      <Option name="capstyle" type="QString" value="round"/>
      <Option name="customdash" type="QString" value="5;2"/>
      <Option name="customdash_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="customdash_unit" type="QString" value="MM"/>
      <Option name="dash_pattern_offset" type="QString" value="0"/>
      <Option name="dash_pattern_offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="dash_pattern_offset_unit" type="QString" value="MM"/>
      <Option name="draw_inside_polygon" type="QString" value="0"/>
      <Option name="joinstyle" type="QString" value="round"/>
      <Option name="line_color" type="QString" value="190,221,243,255,rgb:0.7450981,0.8666667,0.9529412,1"/>
      <Option name="line_style" type="QString" value="solid"/>
      <Option name="line_width" type="QString" value="0"/>
      <Option name="line_width_unit" type="QString" value="MM"/>
      <Option name="offset" type="QString" value="0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="ring_filter" type="QString" value="0"/>
      <Option name="trim_distance_end" type="QString" value="0"/>
      <Option name="trim_distance_end_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="trim_distance_end_unit" type="QString" value="MM"/>
      <Option name="trim_distance_start" type="QString" value="0"/>
      <Option name="trim_distance_start_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="trim_distance_start_unit" type="QString" value="MM"/>
      <Option name="tweak_dash_pattern_on_corners" type="QString" value="0"/>
      <Option name="use_custom_dash" type="QString" value="0"/>
      <Option name="width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties" type="Map">
        <Option name="enabled" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="(CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 9 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),9,10,0,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 15 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),10,15,2,4)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 15 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 17 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),15,17,4,8)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 17 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 18 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),17,18,8,17)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 18 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 20 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),18,20,17,50)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 20 THEN 13.2292 END) > 0"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineWidth" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 9 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),9,10,0,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 15 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),10,15,2,4)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 15 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 17 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),15,17,4,8)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 17 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 18 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),17,18,8,17)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 18 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 20 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),18,20,17,50)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 20 THEN 13.2292 END"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="2" type="line">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleLine" enabled="1" id="{f9a9c55b-a20d-4309-b65e-6801edba19eb}" locked="0" pass="2">
     <Option type="Map">
      <Option name="align_dash_pattern" type="QString" value="0"/>
      <Option name="capstyle" type="QString" value="round"/>
      <Option name="customdash" type="QString" value="5;2"/>
      <Option name="customdash_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="customdash_unit" type="QString" value="MM"/>
      <Option name="dash_pattern_offset" type="QString" value="0"/>
      <Option name="dash_pattern_offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="dash_pattern_offset_unit" type="QString" value="MM"/>
      <Option name="draw_inside_polygon" type="QString" value="0"/>
      <Option name="joinstyle" type="QString" value="round"/>
      <Option name="line_color" type="QString" value="190,221,243,255,rgb:0.7450981,0.8666667,0.9529412,1"/>
      <Option name="line_style" type="QString" value="solid"/>
      <Option name="line_width" type="QString" value="0"/>
      <Option name="line_width_unit" type="QString" value="MM"/>
      <Option name="offset" type="QString" value="0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="ring_filter" type="QString" value="0"/>
      <Option name="trim_distance_end" type="QString" value="0"/>
      <Option name="trim_distance_end_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="trim_distance_end_unit" type="QString" value="MM"/>
      <Option name="trim_distance_start" type="QString" value="0"/>
      <Option name="trim_distance_start_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="trim_distance_start_unit" type="QString" value="MM"/>
      <Option name="tweak_dash_pattern_on_corners" type="QString" value="0"/>
      <Option name="use_custom_dash" type="QString" value="0"/>
      <Option name="width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties" type="Map">
        <Option name="enabled" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="(CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 13 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 14 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),13,14,0,1)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 14 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 15 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),14,15,1,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 15 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 17 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),15,17,2,6)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 17 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 18 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),17,18,6,12)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 18 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 20 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),18,20,12,30)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 20 THEN 7.9375 END) > 0"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineWidth" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 13 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 14 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),13,14,0,1)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 14 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 15 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),14,15,1,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 15 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 17 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),15,17,2,6)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 17 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 18 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),17,18,6,12)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 18 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 20 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),18,20,12,30)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 20 THEN 7.9375 END"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="3" type="line">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleLine" enabled="1" id="{708ed0da-94fc-4802-9428-e1e9db42d92e}" locked="0" pass="3">
     <Option type="Map">
      <Option name="align_dash_pattern" type="QString" value="0"/>
      <Option name="capstyle" type="QString" value="round"/>
      <Option name="customdash" type="QString" value="5;2"/>
      <Option name="customdash_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="customdash_unit" type="QString" value="MM"/>
      <Option name="dash_pattern_offset" type="QString" value="0"/>
      <Option name="dash_pattern_offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="dash_pattern_offset_unit" type="QString" value="MM"/>
      <Option name="draw_inside_polygon" type="QString" value="0"/>
      <Option name="joinstyle" type="QString" value="round"/>
      <Option name="line_color" type="QString" value="190,221,243,255,rgb:0.7450981,0.8666667,0.9529412,1"/>
      <Option name="line_style" type="QString" value="solid"/>
      <Option name="line_width" type="QString" value="0"/>
      <Option name="line_width_unit" type="QString" value="MM"/>
      <Option name="offset" type="QString" value="0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="ring_filter" type="QString" value="0"/>
      <Option name="trim_distance_end" type="QString" value="0"/>
      <Option name="trim_distance_end_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="trim_distance_end_unit" type="QString" value="MM"/>
      <Option name="trim_distance_start" type="QString" value="0"/>
      <Option name="trim_distance_start_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="trim_distance_start_unit" type="QString" value="MM"/>
      <Option name="tweak_dash_pattern_on_corners" type="QString" value="0"/>
      <Option name="use_custom_dash" type="QString" value="0"/>
      <Option name="width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties" type="Map">
        <Option name="enabled" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="(CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 14 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 15 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),14,15,0,1)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 15 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 17 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),15,17,1,4)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 17 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 18 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),17,18,4,8)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 18 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 20 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),18,20,8,20)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 20 THEN 5.29167 END) > 0"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineWidth" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 14 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 15 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),14,15,0,1)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 15 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 17 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),15,17,1,4)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 17 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 18 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),17,18,4,8)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 18 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 20 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),18,20,8,20)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 20 THEN 5.29167 END"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
  </symbols>
  <data-defined-properties>
   <Option type="Map">
    <Option name="name" type="QString" value=""/>
    <Option name="properties"/>
    <Option name="type" type="QString" value="collection"/>
   </Option>
  </data-defined-properties>
 </renderer-v2>
 <selection mode="Default">
  <selectionColor invalid="1"/>
 </selection>
 <blendMode>0</blendMode>
 <featureBlendMode>0</featureBlendMode>
 <layerOpacity>1</layerOpacity>
 <layerGeometryType>1</layerGeometryType>
</qgis>
