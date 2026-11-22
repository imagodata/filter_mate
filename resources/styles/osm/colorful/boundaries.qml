<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis autoRefreshMode="Disabled" autoRefreshTime="0" hasScaleBasedVisibilityFlag="0" labelsEnabled="0" layerType="Vector" maxScale="0" minScale="100000000" simplifyAlgorithm="0" simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyLocal="1" simplifyMaxScale="1" styleCategories="Symbology|Labeling|Rendering" symbologyReferenceScale="-1" version="4.3.0-Master">
 <renderer-v2 enableorderby="0" forceraster="0" referencescale="-1" symbollevels="1" type="RuleRenderer">
  <rules key="{0963ea29-c879-4651-a4b3-69016582bf97}">
   <rule filter="&quot;admin_level&quot; IS '2'" key="{87719a97-1848-4a22-80b4-ab0a7aa96ba8}" label="boundaries:boundary-country:outline" symbol="0"/>
   <rule filter="&quot;admin_level&quot; IS '4'" key="{c44aa2d5-6f2a-4668-8925-09f2f2cf2845}" label="boundaries:boundary-state:outline" symbol="1"/>
   <rule filter="&quot;admin_level&quot; IS '2'" key="{4618e00b-d747-4d94-8d42-09652a3053ea}" label="boundaries:boundary-country" symbol="2"/>
   <rule filter="&quot;admin_level&quot; IS '4'" key="{e0d87bfb-b0c4-4bef-be17-c1f6f944eb03}" label="boundaries:boundary-state" symbol="3"/>
  </rules>
  <symbols>
   <symbol alpha="0.75" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="0" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleLine" enabled="1" id="{c7083183-4529-4fff-8882-9f5abd347968}" locked="0" pass="0">
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
      <Option name="line_color" type="QString" value="249,245,239,255,rgb:0.9764706,0.9607843,0.9372549,1"/>
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
         <Option name="expression" type="QString" value="(CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 2 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 3 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),2,3,0,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 3 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),3,10,2,8)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 THEN 2.11667 END) > 0"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineWidth" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 2 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 3 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),2,3,0,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 3 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),3,10,2,8)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 THEN 2.11667 END"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="0.75" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="1" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleLine" enabled="1" id="{840ffe88-9013-4e1f-9e13-3e748f63c8ae}" locked="0" pass="1">
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
      <Option name="line_color" type="QString" value="250,245,240,255,rgb:0.9803922,0.9607843,0.9411765,1"/>
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
         <Option name="expression" type="QString" value="(CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 7 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 8 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),7,8,0,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 8 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),8,10,2,4)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 THEN 1.05833 END) > 0"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineWidth" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 7 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 8 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),7,8,0,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 8 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),8,10,2,4)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 THEN 1.05833 END"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="2" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleLine" enabled="1" id="{cd8e2e26-3441-42aa-a080-9736635b55a4}" locked="0" pass="2">
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
      <Option name="line_color" type="QString" value="166,166,200,255,rgb:0.6509804,0.6509804,0.7843137,1"/>
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
         <Option name="expression" type="QString" value="(CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 2 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 3 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),2,3,0,1)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 3 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),3,10,1,4)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 THEN 1.05833 END) > 0"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineWidth" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 2 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 3 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),2,3,0,1)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 3 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),3,10,1,4)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 THEN 1.05833 END"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="3" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleLine" enabled="1" id="{daa6f886-5b66-44a0-b882-7791b2e0d9a3}" locked="0" pass="3">
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
      <Option name="line_color" type="QString" value="166,166,200,255,rgb:0.6509804,0.6509804,0.7843137,1"/>
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
         <Option name="expression" type="QString" value="(CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 7 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 8 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),7,8,0,1)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 8 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),8,10,1,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 THEN 0.529167 END) > 0"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineWidth" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="CASE WHEN (log(2, 559082264.0287178 / @map_scale)) >= 7 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 8 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),7,8,0,1)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 8 AND (log(2, 559082264.0287178 / @map_scale)) &lt;= 10 THEN (scale_linear((log(2, 559082264.0287178 / @map_scale)),8,10,1,2)) * 0.264583 WHEN (log(2, 559082264.0287178 / @map_scale)) > 10 THEN 0.529167 END"/>
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
 <layerGeometryType>2</layerGeometryType>
</qgis>
