<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis autoRefreshMode="Disabled" autoRefreshTime="0" hasScaleBasedVisibilityFlag="0" labelsEnabled="0" layerType="Vector" maxScale="0" minScale="100000000" simplifyAlgorithm="0" simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyLocal="1" simplifyMaxScale="1" styleCategories="Symbology|Labeling|Rendering" symbologyReferenceScale="-1" version="4.3.0-Master">
 <renderer-v2 enableorderby="0" forceraster="0" referencescale="-1" symbollevels="1" type="RuleRenderer">
  <rules key="{9863d016-578c-4d10-a400-153490639159}">
   <rule filter="&quot;building&quot; IS NOT NULL" key="{c489f62e-144c-4ed5-ab26-7543d5c6deac}" label="buildings:building:outline" symbol="0"/>
   <rule filter="&quot;building&quot; IS NOT NULL" key="{1435b28e-c466-4fc0-ad50-02c501194a9c}" label="buildings:building" symbol="1"/>
  </rules>
  <symbols>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="0" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{99790cb9-3cbd-4d1d-8134-05ce8ecbdf82}" locked="0" pass="0">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="223,219,215,255,rgb:0.8745098,0.8588235,0.8431373,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="223,219,215,255,rgb:0.8745098,0.8588235,0.8431373,1"/>
      <Option name="outline_style" type="QString" value="solid"/>
      <Option name="outline_width" type="QString" value="0"/>
      <Option name="outline_width_unit" type="QString" value="MM"/>
      <Option name="style" type="QString" value="solid"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties" type="Map">
        <Option name="fillColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),14,15,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),14,15,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="1" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{7c0d5800-c18b-4127-89a3-0c49d2687124}" locked="0" pass="1">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="242,234,226,255,rgb:0.9490196,0.9176471,0.8862745,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="-0.52916666666666667,-0.52916666666666667"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="242,234,226,255,rgb:0.9490196,0.9176471,0.8862745,1"/>
      <Option name="outline_style" type="QString" value="solid"/>
      <Option name="outline_width" type="QString" value="0"/>
      <Option name="outline_width_unit" type="QString" value="MM"/>
      <Option name="style" type="QString" value="solid"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties" type="Map">
        <Option name="fillColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),14,15,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),14,15,0,255))"/>
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
