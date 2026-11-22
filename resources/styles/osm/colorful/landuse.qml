<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis autoRefreshMode="Disabled" autoRefreshTime="0" hasScaleBasedVisibilityFlag="0" labelsEnabled="0" layerType="Vector" maxScale="0" minScale="100000000" simplifyAlgorithm="0" simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyLocal="1" simplifyMaxScale="1" styleCategories="Symbology|Labeling|Rendering" symbologyReferenceScale="-1" version="4.3.0-Master">
 <renderer-v2 enableorderby="0" forceraster="0" referencescale="-1" symbollevels="1" type="RuleRenderer">
  <rules key="{1c2eab06-3c64-4b05-a537-15a162397d5f}">
   <rule filter="&quot;landuse&quot; IN ('commercial', 'retail')" key="{d62b1915-a52e-4f30-a3bd-7669d6d8241b}" label="landuse:land-commercial" symbol="0"/>
   <rule filter="&quot;landuse&quot; IN ('industrial', 'quarry', 'railway')" key="{57866ea6-1d42-432b-921a-117b6d1e0bcf}" label="landuse:land-industrial" symbol="1"/>
   <rule filter="&quot;landuse&quot; IN ('garages', 'residential')" key="{614e92d4-377f-429e-a94e-8cc20d5c56f7}" label="landuse:land-residential" symbol="2"/>
   <rule filter="&quot;landuse&quot; IN ('brownfield', 'farmland', 'farmyard', 'greenfield', 'greenhouse_horticulture', 'orchard', 'plant_nursery', 'vineyard')" key="{a8e09132-98a7-4ef1-aa27-15f3c4e603a8}" label="landuse:land-agriculture" symbol="3"/>
   <rule filter="&quot;landuse&quot; IS 'landfill'" key="{90f271b2-b549-440b-8c0d-e29dd4fda561}" label="landuse:land-waste" symbol="4"/>
   <rule filter="&quot;landuse&quot; IN ('recreation_ground', 'village_green')" key="{08fe488b-5d54-46bb-9328-7c1903ac2257}" label="landuse:land-park" symbol="5"/>
   <rule filter="&quot;landuse&quot; IS 'allotments'" key="{7a069921-d591-44db-9d24-2df875c0a326}" label="landuse:land-garden" symbol="6"/>
   <rule filter="&quot;landuse&quot; IS 'cemetery'" key="{a179712a-23ef-46fd-bda2-e33371bf1db2}" label="landuse:land-burial" symbol="7"/>
   <rule filter="&quot;landuse&quot; IS 'forest'" key="{18bfbb2c-ce5e-4002-909d-7c0de3dc9cec}" label="landuse:land-forest" symbol="8"/>
   <rule filter="&quot;landuse&quot; IN ('grass', 'meadow')" key="{1c07d1fb-595b-43f3-86a4-bddaf95593b6}" label="landuse:land-grass" symbol="9"/>
   <rule filter="&quot;landuse&quot; IN ('basin', 'reservoir')" key="{798727b5-65dc-4bdd-b15c-981a9c988aae}" label="landuse:water-area-small" symbol="10"/>
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
    <layer class="SimpleFill" enabled="1" id="{c7bd7304-c3bb-47ae-9ba9-c1d68bd485b3}" locked="0" pass="0">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="247,222,237,64,rgb:0.9686275,0.8705882,0.9294118,0.2509804"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1"/>
      <Option name="outline_style" type="QString" value="no"/>
      <Option name="outline_width" type="QString" value="0.26"/>
      <Option name="outline_width_unit" type="QString" value="MM"/>
      <Option name="style" type="QString" value="solid"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties" type="Map">
        <Option name="fillColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,64))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,64))"/>
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
    <layer class="SimpleFill" enabled="1" id="{cae54a02-75d2-4d16-a236-c03fe991deb8}" locked="0" pass="1">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="255,244,194,85,rgb:1,0.9568627,0.7607843,0.3333333"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1"/>
      <Option name="outline_style" type="QString" value="no"/>
      <Option name="outline_width" type="QString" value="0.26"/>
      <Option name="outline_width_unit" type="QString" value="MM"/>
      <Option name="style" type="QString" value="solid"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties" type="Map">
        <Option name="fillColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,85))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,85))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="10" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{bd470715-edf5-4423-b2fd-1d58059c8657}" locked="0" pass="10">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="190,221,243,255,rgb:0.7450981,0.8666667,0.9529412,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="190,221,243,255,rgb:0.7450981,0.8666667,0.9529412,1"/>
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
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),4,6,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),4,6,0,255))"/>
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
    <layer class="SimpleFill" enabled="1" id="{207408f6-f699-4ae1-95aa-adb7828e40a8}" locked="0" pass="2">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="234,230,225,51,rgb:0.9176471,0.9019608,0.8823529,0.2"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1"/>
      <Option name="outline_style" type="QString" value="no"/>
      <Option name="outline_width" type="QString" value="0.26"/>
      <Option name="outline_width_unit" type="QString" value="MM"/>
      <Option name="style" type="QString" value="solid"/>
     </Option>
     <data_defined_properties>
      <Option type="Map">
       <Option name="name" type="QString" value=""/>
       <Option name="properties" type="Map">
        <Option name="fillColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,51))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,51))"/>
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
    <layer class="SimpleFill" enabled="1" id="{7edd1502-eae9-4a94-8248-88744d5d068f}" locked="0" pass="3">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="240,231,209,255,rgb:0.9411765,0.9058824,0.8196079,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="240,231,209,255,rgb:0.9411765,0.9058824,0.8196079,1"/>
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
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="4" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{309214b2-d56e-4224-a014-7917bad3f5fc}" locked="0" pass="4">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="219,214,189,255,rgb:0.8588235,0.8392157,0.7411765,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="219,214,189,255,rgb:0.8588235,0.8392157,0.7411765,1"/>
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
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),10,11,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="5" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{f36c2d65-5c6a-4014-ab91-a0cef7e51300}" locked="0" pass="5">
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
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="6" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{a4c4b658-eb02-42cc-aa74-445c2311f6a7}" locked="0" pass="6">
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
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="7" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{030544d5-11d6-4a5e-87bd-193dec680574}" locked="0" pass="7">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="221,219,202,255,rgb:0.8666667,0.8588235,0.7921569,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="221,219,202,255,rgb:0.8666667,0.8588235,0.7921569,1"/>
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
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),13,14,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),13,14,0,255))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="8" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{feea1432-f2d9-43a6-999a-86ea83abf6ad}" locked="0" pass="8">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="102,170,68,255,rgb:0.4,0.6666667,0.2666667,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="102,170,68,255,rgb:0.4,0.6666667,0.2666667,1"/>
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
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),7,8,0,25.5))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
        <Option name="outlineColor" type="Map">
         <Option name="active" type="bool" value="true"/>
         <Option name="expression" type="QString" value="set_color_part(@symbol_color, 'alpha', scale_linear((log(2, 559082264.0287178 / @map_scale)),7,8,0,25.5))"/>
         <Option name="type" type="int" value="3"/>
        </Option>
       </Option>
       <Option name="type" type="QString" value="collection"/>
      </Option>
     </data_defined_properties>
    </layer>
   </symbol>
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="9" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{8702ee1f-72f7-419c-903f-72462d19610c}" locked="0" pass="9">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="216,232,200,255,rgb:0.8470588,0.9098039,0.7843137,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="216,232,200,255,rgb:0.8470588,0.9098039,0.7843137,1"/>
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
