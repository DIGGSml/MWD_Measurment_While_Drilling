import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import date

# Register necessary namespaces
namespaces = {
    '': 'http://diggsml.org/schemas/2.6',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xlink': 'http://www.w3.org/1999/xlink',
    'gml': 'http://www.opengis.net/gml/3.2',
    'g3.3': 'http://www.opengis.net/gml/3.3/ce',
    'glr': 'http://www.opengis.net/gml/3.3/lr',
    'glrov': 'http://www.opengis.net/gml/3.3/lrov',
    'diggs_geo': 'http://diggsml.org/schemas/2.6/geotechnical',
    'witsml': 'http://www.witsml.org/schemas/131',
    'diggs': 'http://diggsml.org/schemas/2.6'
}

for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)

# Parse the structured text file
header_data = {}
parameter_data = {}
data_rows = []

with open('/workspaces/MWD_Measurment_While_Drilling/3_11_B-2.guh', 'r') as file:
    section = None
    for line in file:
        line = line.strip()
        if line.startswith('[HEADER]'):
            section = 'header'
        elif line.startswith('[PARAMETER]'):
            section = 'parameter'
        elif line.startswith('[DATA]'):
            section = 'data'
        elif line.startswith('[FOOTER]'):
            section = 'footer'
        else:
            if section == 'header':
                if '=' in line:
                    key, value = line.split('=')
                    header_data[key] = value
            elif section == 'parameter':
                if 'parameter_names' not in parameter_data:
                    parameter_data['parameter_names'] = line.split(';')
                elif 'parameter_units' not in parameter_data:
                    parameter_data['parameter_units'] = line.split(';')
            elif section == 'data':
                row = line.split(';')
                # Convert depth to positive value
                if len(row) > 1:
                    row[1] = str(abs(float(row[1])))
                data_rows.append(row)

max_depth = max(abs(float(row[1])) for row in data_rows if len(row) > 1)

# Create the DIGGS XML structure
print(parameter_data)
root = ET.Element('Diggs', {
    'xmlns': 'http://diggsml.org/schemas/2.6',
    'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xmlns:xlink': 'http://www.w3.org/1999/xlink',
    'xmlns:gml': 'http://www.opengis.net/gml/3.2',
    'xmlns:g3.3': 'http://www.opengis.net/gml/3.3/ce',
    'xmlns:glr': 'http://www.opengis.net/gml/3.3/lr',
    'xmlns:glrov': 'http://www.opengis.net/gml/3.3/lrov',
    'xmlns:diggs_geo': 'http://diggsml.org/schemas/2.6/geotechnical',
    'xmlns:witsml': 'http://www.witsml.org/schemas/131',
    'xmlns:diggs': 'http://diggsml.org/schemas/2.6',
    'xsi:schemaLocation': 'http://diggsml.org/schemas/2.6 http://diggsml.org/schemas/2.6/Diggs.xsd',
    'gml:id': 'Github_Exported'
})

# Add document information
document_info = ET.SubElement(root, 'documentInformation')
document_info_element = ET.SubElement(document_info, 'DocumentInformation', {'gml:id': 'mwd_guh_2_DIGGS'})
ET.SubElement(document_info_element, 'creationDate').text = date.today().isoformat()
audit_trail = ET.SubElement(document_info_element, 'auditTrail')
remark = ET.SubElement(audit_trail, 'Remark')
ET.SubElement(remark, 'content').text = 'mwd_guh_2_DIGGS'

# Add project information
project = ET.SubElement(root, 'project')
project_element = ET.SubElement(project, 'Project', {'gml:id': 'p1'})
ET.SubElement(project_element, 'gml:name').text = 'mwd_guh_2_DIGGS'
role = ET.SubElement(project_element, 'role')
role_element = ET.SubElement(role, 'Role')
ET.SubElement(role_element, 'rolePerformed').text = 'Client'
business_associate = ET.SubElement(role_element, 'businessAssociate')
business_associate_element = ET.SubElement(business_associate, 'BusinessAssociate', {'gml:id': 'businessAssociate_3890831877466659_Num_0'})
ET.SubElement(business_associate_element, 'gml:name').text = header_data['Contractor']
ET.SubElement(project_element, 'purpose').text = 'mwd_guh_2_DIGGS'

# Add sampling feature
sampling_feature = ET.SubElement(root, 'samplingFeature')
borehole = ET.SubElement(sampling_feature, 'Borehole', {'gml:id': 'Borehole_Num_1'})
ET.SubElement(borehole, 'gml:name').text = header_data['BoreholeID']
ET.SubElement(borehole, 'investigationTarget').text = 'Natural Ground'
ET.SubElement(borehole, 'projectRef', {'xlink:href': '#p1'})

# Add referencePoint
reference_point = ET.SubElement(borehole, 'referencePoint')
point_location = ET.SubElement(reference_point, 'PointLocation', {'gml:id': 'Point_Location3890831877466659_Num_0-pl'})
pos = ET.SubElement(point_location, 'gml:pos', {
    'srsDimension': '3',
    'srsName': 'urn:diggs:def:crs:DIGGS:0.1:4326_5702',
    'uomLabels': 'degrees'
})
pos.text = '-77.466659 38.908318 244.34'

# Add centerLine
center_line = ET.SubElement(borehole, 'centerLine')
linear_extent = ET.SubElement(center_line, 'LinearExtent', {'gml:id': 'Linear_Extent_0'})
pos_list = ET.SubElement(linear_extent, 'gml:posList')
pos_list.text = '-77.466659 38.908318 244.34 38.908318 -77.466659 219.14000000000001'

# Add linearReferencing
linear_referencing = ET.SubElement(borehole, 'linearReferencing')
lsrs = ET.SubElement(linear_referencing, 'LinearSpatialReferenceSystem', {'gml:id': 'lrs'})
ET.SubElement(lsrs, 'gml:identifier', {'codeSpace': ''})
ET.SubElement(lsrs, 'glr:linearElement', {'xlink:href': '#Linear_Extent_0'})
lrm = ET.SubElement(lsrs, 'glr:lrm')
lrm_method = ET.SubElement(lrm, 'glr:LinearReferencingMethod', {'gml:id': 'Linear_Extent_0_'})
ET.SubElement(lrm_method, 'glr:name').text = 'chainage'
ET.SubElement(lrm_method, 'glr:type').text = 'absolute'
ET.SubElement(lrm_method, 'glr:units').text = 'ft'

# # Add whenConstructed
# when_constructed = ET.SubElement(borehole, 'whenConstructed')
# time_interval = ET.SubElement(when_constructed, 'TimeInterval', {'gml:id': 'time_Num_0'})
# ET.SubElement(time_interval, 'start').text = '9/17/08 - 9/22/08'
# ET.SubElement(time_interval, 'end').text = '9/17/08 - 9/22/08'

# Add totalMeasuredDepth
ET.SubElement(borehole, 'totalMeasuredDepth', {'uom': 'm'}).text = f'{max_depth:.2f}'


# Add measurement data
measurement = ET.SubElement(root, 'measurement')
test = ET.SubElement(measurement, 'Test', {'gml:id': 'test1'})
ET.SubElement(test, 'gml:name').text = 'MWD Test'
ET.SubElement(test, 'investigationTarget').text = 'Natural Ground'
ET.SubElement(test, 'projectRef', {'xlink:href': '#p1'})
ET.SubElement(test, 'samplingFeatureRef', {'xlink:href': '#Borehole_Num_1'})

# Add test result
test_result = ET.SubElement(test, 'outcome')
result_set = ET.SubElement(test_result, 'TestResult', {'gml:id': 'm1'})
# Add location information
location = ET.SubElement(result_set, 'location')
multi_point_location = ET.SubElement(location, 'MultiPointLocation', {
    'srsName': 'urn:ogc:def:crs:EPSG::4326',
    'srsDimension': '1',
    'gml:id': 'loc1'
})
coordinates = []
for row in data_rows:
    if len(row) >= 2:
        depth = float(row[1])
        coordinates.append(f'0 0 {depth}')
ET.SubElement(multi_point_location, 'gml:posList').text = ' '.join(coordinates)

# Add result properties
result_properties = ET.SubElement(result_set, 'results')
result_property_set = ET.SubElement(result_properties, 'ResultSet')
parameters = ET.SubElement(result_property_set, 'parameters')
property_params = ET.SubElement(parameters, 'PropertyParameters', {'gml:id': 'params1'})
properties_element = ET.SubElement(property_params, 'properties')

# Extract parameter names and units from the [PARAMETER] section
if 'parameter_names' in parameter_data and 'parameter_units' in parameter_data:
    parameter_names = parameter_data['parameter_names']
    parameter_units = parameter_data['parameter_units']

    for i, (name, unit) in enumerate(zip(parameter_names, parameter_units), start=1):
        property_element = ET.SubElement(properties_element, 'Property', {
            'gml:id': f'prop{i}',
            'index': str(i)
        })
        ET.SubElement(property_element, 'propertyName').text = name
        ET.SubElement(property_element, 'typeData').text = 'double'
        
        if name == 'Depth':
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#depth'
            }).text = 'depth'
        elif name == 'RateOfPenetration':
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#rate_of_penetration'
            }).text = 'rate_of_penetration'
        elif name == 'RotationShaft':
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#rotation_shaft'
            }).text = 'rotation_shaft'
        elif name == 'RotationTool':
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#rotation_tool'
            }).text = 'rotation_tool'
        elif name == 'Fow':
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#flow_rate'
            }).text = 'flow_rate'
        elif name == 'PressureFlush':
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#pressure_flush'
            }).text = 'pressure_flush'
        elif name == 'PressurePulldown':
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#pressure_pulldown'
            }).text = 'pressure_pulldown'
        elif name == 'RotationTach':
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#rotation_tach'
            }).text = 'rotation_tach'
        elif name == 'TorqueTach':
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#torque_tach'
            }).text = 'torque_tach'
        else:
            ET.SubElement(property_element, 'propertyClass', {
                'codeSpace': 'http://diggsml.org/terms/DIGGSTestPropertyDefinitions.xml#missing'
            }).text = 'missing'
    
            # Only add the uom element if the unit is not '-'
            if unit != '-':
                ET.SubElement(property_element, 'uom').text = unit

        ET.SubElement(property_element, 'nullValue', {'reason': 'missing'}).text = '9999'

# Add result data values
data_values = ET.SubElement(result_property_set, 'dataValues', {'cs': ',', 'ts': ' ', 'decimal': '.'})
data_value_rows = []
for row in data_rows:
    if len(row) >= 3:
        data_value_row = ','.join(row[2:])  # Exclude timestamp and depth
        data_value_rows.append(data_value_row)
data_values.text = '\n'.join(data_value_rows)

# Convert the XML to a pretty-printed string
xml_string = minidom.parseString(ET.tostring(root)).toprettyxml(indent='  ')

# Write the XML to a file
with open('mwd_diggs.xml', 'w') as file:
    file.write(xml_string)
