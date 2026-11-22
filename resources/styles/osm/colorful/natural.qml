<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis autoRefreshMode="Disabled" autoRefreshTime="0" hasScaleBasedVisibilityFlag="0" labelsEnabled="0" layerType="Vector" maxScale="0" minScale="100000000" simplifyAlgorithm="0" simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyLocal="1" simplifyMaxScale="1" styleCategories="Symbology|Labeling|Rendering" symbologyReferenceScale="-1" version="4.3.0-Master">
 <renderer-v2 enableorderby="0" forceraster="0" referencescale="-1" symbollevels="1" type="RuleRenderer">
  <rules key="{451209cc-2b43-44b7-aabf-db1cd823e561}">
   <rule filter="&quot;natural&quot; IS 'glacier'" key="{9a97c06a-dd9f-4dc7-8b15-8bfd6bbd675c}" label="natural:land-glacier" symbol="0"/>
   <rule filter="&quot;natural&quot; IN ('bare_rock', 'scree', 'shingle')" key="{16b797dc-b541-4dbf-a6f5-42622199dcb5}" label="natural:land-rock" symbol="1"/>
   <rule filter="&quot;natural&quot; IS 'wood'" key="{f903f0a8-db49-4bbe-9278-3f12558a26e9}" label="natural:land-forest" symbol="2"/>
   <rule filter="&quot;natural&quot; IS 'grassland'" key="{9007739c-c59f-4525-b8bd-4042cc58755e}" label="natural:land-grass" symbol="3"/>
   <rule filter="&quot;natural&quot; IN ('heath', 'scrub')" key="{4fb8f1df-0c12-403a-9eba-2df0917d59b2}" label="natural:land-vegetation" symbol="4"/>
   <rule filter="&quot;natural&quot; IN ('beach', 'sand')" key="{2ef92cfa-98eb-4aec-9a46-eeaa180c84f9}" label="natural:land-sand" symbol="5"/>
   <rule filter="&quot;natural&quot; IS 'wetland'" key="{5ae777e7-38f3-4f60-81a5-710ec7c519ae}" label="natural:land-wetland" symbol="6"/>
   <rule filter="&quot;natural&quot; IS 'water'" key="{14e6cf2d-3dcf-4041-a9a1-6efc18cda998}" label="natural:water-area" symbol="7"/>
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
    <layer class="SimpleFill" enabled="1" id="{a827dd6c-5182-4366-b315-77b9e90e5bb2}" locked="0" pass="0">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="255,255,255,255,rgb:1,1,1,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="255,255,255,255,rgb:1,1,1,1"/>
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
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="1" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{fc6ce136-800c-4b04-a848-e321e3be3fac}" locked="0" pass="1">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="224,228,229,255,rgb:0.8784314,0.8941177,0.8980392,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="224,228,229,255,rgb:0.8784314,0.8941177,0.8980392,1"/>
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
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="2" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{6f8bdaca-5803-4693-b6b5-4dee503227c7}" locked="0" pass="2">
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
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="3" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{e797620e-0743-462c-9006-cb295ec20445}" locked="0" pass="3">
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
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="4" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{b380e0f2-6a14-4583-b4db-82f2ad3a6c43}" locked="0" pass="4">
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
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="5" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{5080e410-f8ff-466e-b628-e440bf2e2f39}" locked="0" pass="5">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="250,250,237,255,rgb:0.9803922,0.9803922,0.9294118,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="250,250,237,255,rgb:0.9803922,0.9803922,0.9294118,1"/>
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
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="6" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{cd72d535-0d9e-44c1-b173-d259b0949de3}" locked="0" pass="6">
     <Option type="Map">
      <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="color" type="QString" value="211,230,219,255,rgb:0.827451,0.9019608,0.8588235,1"/>
      <Option name="joinstyle" type="QString" value="bevel"/>
      <Option name="offset" type="QString" value="0,0"/>
      <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0"/>
      <Option name="offset_unit" type="QString" value="MM"/>
      <Option name="outline_color" type="QString" value="211,230,219,255,rgb:0.827451,0.9019608,0.8588235,1"/>
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
   <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="7" type="fill">
    <data_defined_properties>
     <Option type="Map">
      <Option name="name" type="QString" value=""/>
      <Option name="properties"/>
      <Option name="type" type="QString" value="collection"/>
     </Option>
    </data_defined_properties>
    <layer class="SimpleFill" enabled="1" id="{bc834e3f-8473-4fd5-a4bd-e57fd3c1859a}" locked="0" pass="7">
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
