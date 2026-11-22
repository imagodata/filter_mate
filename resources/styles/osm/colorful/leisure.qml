<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis autoRefreshMode="Disabled" autoRefreshTime="0" hasScaleBasedVisibilityFlag="0" labelsEnabled="0" layerType="Vector" maxScale="0" minScale="100000000" simplifyAlgorithm="0" simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyLocal="1" simplifyMaxScale="1" styleCategories="Symbology|Labeling|Rendering" symbologyReferenceScale="-1" version="4.3.0-Master">
 <renderer-v2 enableorderby="0" forceraster="0" referencescale="-1" symbollevels="1" type="RuleRenderer">
  <rules key="{6152c324-ef7c-4496-83c0-a4ee0e396ec7}">
   <rule filter="&quot;leisure&quot; IS 'park'" key="{f097a7c6-a9c1-431a-ae75-f32f0ffc91a7}" label="leisure:land-park" symbol="0"/>
   <rule filter="&quot;leisure&quot; IS 'garden'" key="{010a1acf-c69c-4d95-ba43-ebf7671ae82a}" label="leisure:land-garden" symbol="1"/>
   <rule filter="&quot;leisure&quot; IN ('golf_course', 'miniature_golf', 'playground')" key="{eb1eac87-5ec6-44b5-8b8b-0f3aa29acf90}" label="leisure:land-leisure" symbol="2"/>
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
    <layer class="SimpleFill" enabled="1" id="{10f57339-22f5-4450-aa91-e40cb33039a4}" locked="0" pass="0">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="217,217,165,255,rgb:0.8509804,0.8509804,0.6470588,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="217,217,165,255,rgb:0.8509804,0.8509804,0.6470588,1"/>
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
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),11,12,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),11,12,0,255))"/>
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
    <layer class="SimpleFill" enabled="1" id="{3312a22d-055c-4982-b4f7-c45d318ad288}" locked="0" pass="1">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="217,217,165,255,rgb:0.8509804,0.8509804,0.6470588,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="217,217,165,255,rgb:0.8509804,0.8509804,0.6470588,1"/>
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
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),11,12,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),11,12,0,255))"/>
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
    <layer class="SimpleFill" enabled="1" id="{6b7f007b-beca-41bc-ac38-32922dc119ac}" locked="0" pass="2">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="231,237,222,255,rgb:0.9058824,0.9294118,0.8705882,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="231,237,222,255,rgb:0.9058824,0.9294118,0.8705882,1"/>
      <Option name="outline_style" type="QString" value="solid"/>
      <Option name="outline_width" type="QString" value="0"/>
      <Option name="outline_width_unit" type="QString" value="MM"/>
      <Option name="style" type="QString" value="solid"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties"/>
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
