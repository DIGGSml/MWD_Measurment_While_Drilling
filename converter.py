import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, date

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

def parse_input_file(file_path):
    header_data = {}
    parameter_data = {}
    data_rows = []

    with open(file_path, 'r') as file:
        section = None
        for line in file:
            line = line.strip()
            if line.startswith('[HEADER]'):
                section = 'header'
            elif line.startswith('[PARAMETER]'):
                section = 'parameter'
            elif line.startswith('[DATA]'):
                section = 'data'
            elif line == '':
                continue
            else:
                if section == 'header':
                    if '=' in line:
                        key, value = line.split('=')
                        # Remove leading/trailing zeros for coordinate fields
                        if key.strip() in ['Latitude_Modem', 'Longitude_Modem', 'Altitude_Modem']:
                            value = value.lstrip('0') or '0'  # Keep at least one zero if all zeros
                        header_data[key.strip()] = value.strip()
                elif section == 'parameter':
                    if 'parameter_names' not in parameter_data:
                        parameter_data['parameter_names'] = line.split(';')
                    elif 'parameter_units' not in parameter_data:
                        parameter_data['parameter_units'] = line.split(';')
                elif section == 'data':
                    if line.startswith('Datum'):
                        continue
                    row = line.split(';')
                    data_rows.append(row)

    return header_data, parameter_data, data_rows

def create_diggs_xml(header_data, parameter_data, data_rows):
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
        'xsi:schemaLocation': 'http://diggsml.org/schemas/2.6 https://diggsml.org/schema-dev/Diggs.xsd',
        'gml:id': 'Github_Exported'
    })

    # Add document information
    add_document_information(root)

    # Add project information
    add_project_information(root, header_data)

    # Add sampling feature (borehole)
    add_sampling_feature(root, header_data,data_rows)

    # Add measurement data
    add_measurement_data(root, header_data, parameter_data, data_rows)

    return root

def add_document_information(root):
    document_info = ET.SubElement(root, 'documentInformation')
    doc_info_element = ET.SubElement(document_info, 'DocumentInformation', {'gml:id': 'mwd_guh_2_DIGGS'})
    ET.SubElement(doc_info_element, 'creationDate').text = date.today().isoformat()

def add_project_information(root, header_data):
    project = ET.SubElement(root, 'project')
    project_element = ET.SubElement(project, 'Project', {'gml:id': 'p1'})
    ET.SubElement(project_element, 'gml:name').text = 'mwd_guh_2_DIGGS'
    
    role = ET.SubElement(project_element, 'role')
    role_element = ET.SubElement(role, 'Role')
    ET.SubElement(role_element, 'rolePerformed', {
        'codeSpace': 'https://diggsml.org/def/codes/DIGGS/0.1/roles.xml'
    }).text = 'drilling_contractor'
    business_associate = ET.SubElement(role_element, 'businessAssociate')
    business_associate_element = ET.SubElement(business_associate, 'BusinessAssociate', {'gml:id': 'businessAssociate_3890831877466659_Num_0'})
    ET.SubElement(business_associate_element, 'gml:name').text = header_data.get('Contractor', '')

def add_sampling_feature(root, header_data, data_rows):
    sampling_feature = ET.SubElement(root, 'samplingFeature')
    borehole = ET.SubElement(sampling_feature, 'Borehole', {'gml:id': f"id_{header_data.get('BoreholeID', 'Unknown')}"})
    ET.SubElement(borehole, 'gml:name').text = header_data.get('BoreholeID', '')
    ET.SubElement(borehole, 'investigationTarget').text = 'Natural Ground'
    ET.SubElement(borehole, 'projectRef', {'xlink:href': '#p1'})

    add_reference_point(borehole, header_data)
    add_center_line(borehole, header_data, data_rows)
    add_linear_referencing(borehole)
    add_total_measured_depth(borehole, data_rows)
    add_casing(borehole, header_data)
    add_construction_method(borehole, header_data, data_rows)  # Pass data_rows here

def add_reference_point(borehole, header_data):
    reference_point = ET.SubElement(borehole, 'referencePoint')
    point_location = ET.SubElement(reference_point, 'PointLocation', {'gml:id': 'Point_Location3890831877466659_Num_0-pl'})
    
    # Convert coordinate strings to floats and format them
    try:
        latitude = float(header_data.get('Latitude_Modem', '0'))
        longitude = float(header_data.get('Longitude_Modem', '0'))
        altitude = float(header_data.get('Altitude_Modem', '0'))
        
        # Format coordinates to 6 decimal places
        coord_string = f"{latitude:.6f} {longitude:.6f} {altitude:.2f}"
    except ValueError:
        # If conversion fails, use a default or log an error
        print("Warning: Invalid coordinate data in header. Using default values.")
        coord_string = "0.000000 0.000000 0.00"

    pos = ET.SubElement(point_location, 'gml:pos', {
        'srsDimension': '3',
        'uomLabels': 'dega dega m',
        'axisLabels': 'latitude longitude height'
    })
    pos.text = coord_string

def add_center_line(borehole, header_data, data_rows):
    center_line = ET.SubElement(borehole, 'centerLine')
    linear_extent = ET.SubElement(center_line, 'LinearExtent', {'gml:id': 'Linear_Extent_0'})
    pos_list = ET.SubElement(linear_extent, 'gml:posList', {
        'srsDimension': '3',
        'uomLabels': 'dega dega m',
        'axisLabels': 'latitude longitude height'
    })
    start_depth = f"{header_data.get('Latitude_Modem', '0')} {header_data.get('Longitude_Modem', '0')} {header_data.get('Altitude_Modem', '0')}"
    end_depth = f"{header_data.get('Latitude_Modem', '0')} {header_data.get('Longitude_Modem', '0')} -{float(header_data.get('Altitude_Modem', '0')) - float(data_rows[-1][1])}"
    pos_list.text = f"{start_depth} {end_depth}"

def add_linear_referencing(borehole):
    linear_referencing = ET.SubElement(borehole, 'linearReferencing')
    lsrs = ET.SubElement(linear_referencing, 'LinearSpatialReferenceSystem', {'gml:id': 'lrs'})
    ET.SubElement(lsrs, 'gml:identifier', {'codeSpace': 'DIGGS'}).text = 'DIGGS:lrs'
    ET.SubElement(lsrs, 'glr:linearElement', {'xlink:href': '#Linear_Extent_0'})
    lrm = ET.SubElement(lsrs, 'glr:lrm')
    lrm_method = ET.SubElement(lrm, 'glr:LinearReferencingMethod', {'gml:id': 'Linear_Extent_0_'})
    ET.SubElement(lrm_method, 'glr:name').text = 'chainage'
    ET.SubElement(lrm_method, 'glr:type').text = 'absolute'
    ET.SubElement(lrm_method, 'glr:units').text = 'm'

def add_total_measured_depth(borehole, data_rows):
    max_depth = max(abs(float(row[1])) for row in data_rows)
    ET.SubElement(borehole, 'totalMeasuredDepth', {'uom': 'm'}).text = f'{max_depth:.2f}'

def add_casing(borehole, header_data):
    casing = ET.SubElement(borehole, 'casing')
    casing_element = ET.SubElement(casing, 'Casing', {'gml:id': f"id_{header_data.get('BoreholeID', 'Unknown')}_casing1"})
    ET.SubElement(casing_element, 'casingOutsideDiameter', {'uom': 'in'}).text = header_data.get('CasingOD(inch)', '')

def add_construction_method(borehole, header_data, data_rows):
    construction_method = ET.SubElement(borehole, 'constructionMethod')
    method_element = ET.SubElement(construction_method, 'BoreholeConstructionMethod', {'gml:id': f"{header_data.get('BoreholeID', 'Unknown')}_cons_method1"})
    ET.SubElement(method_element, 'gml:name').text = 'Auger'
    
    # Add location element
    location = ET.SubElement(method_element, 'location')
    linear_extent = ET.SubElement(location, 'LinearExtent', {'gml:id': f"{header_data.get('BoreholeID', 'Unknown')}_cons_method1_le"})
    
    # Calculate total depth
    total_depth = max(abs(float(row[1])) for row in data_rows)
    
    pos_list = ET.SubElement(linear_extent, 'gml:posList', {'srsName': '#lrs', 'srsDimension': '1'})
    pos_list.text = f"0 {total_depth:.2f}"
    
    add_construction_equipment(method_element, header_data)

def add_construction_equipment(method_element, header_data):
    # Add DrillRig
    construction_equipment_drill = ET.SubElement(method_element, 'constructionEquipment')
    
    client_info = header_data.get('Client', '').strip()
    make, model = parse_client_info(client_info)
    
    drill_rig = ET.SubElement(construction_equipment_drill, 'DrillRig', {'gml:id': client_info.replace(' ', '')})
    ET.SubElement(drill_rig, 'gml:name').text = client_info
    ET.SubElement(drill_rig, 'make').text = make
    ET.SubElement(drill_rig, 'modelNumber').text = model
    
    for i in range(1, 6):
        ET.SubElement(drill_rig, 'rotaryDriveGearRatio', {'gearNumber': str(i)}).text = header_data.get(f'Ratio_G{i}', '')
    
    ET.SubElement(drill_rig, 'crowdCylinderArea', {'uom': 'in2'}).text = header_data.get('CrowdCylArea', '0.00')
    
    add_cutting_tool_info(drill_rig, header_data)

    # Add CoringDevice
    construction_equipment_core = ET.SubElement(method_element, 'constructionEquipment')
    coring_device = ET.SubElement(construction_equipment_core, 'CoringDevice', {'gml:id': 'rockcore1'})
    ET.SubElement(coring_device, 'gml:name').text = 'Rock core'
    
    rock_core_size = header_data.get('RockCoreSize(inch)', '0')
    ET.SubElement(coring_device, 'barrelInnerDiameter', {'uom': 'in'}).text = rock_core_size.split('=')[-1].strip()

def parse_client_info(client_info):
    # Attempt to split the client info into make and model
    parts = client_info.split()
    if len(parts) >= 2:
        make = parts[0]
        model = ' '.join(parts[1:])
    else:
        make = client_info
        model = "Unknown"
    return make, model

def add_cutting_tool_info(drill_rig, header_data):
    cutting_tool_info = ET.SubElement(drill_rig, 'cuttingToolInfo')
    
    auger_tool = ET.SubElement(cutting_tool_info, 'CuttingTool')
    ET.SubElement(auger_tool, 'gml:name').text = 'Auger'
    ET.SubElement(auger_tool, 'toolOuterDiameter', {'uom': 'in'}).text = header_data.get('AugerID', '')
    
    roller_bit_tool = ET.SubElement(cutting_tool_info, 'CuttingTool')
    ET.SubElement(roller_bit_tool, 'gml:name').text = 'Roller bit'
    ET.SubElement(roller_bit_tool, 'toolOuterDiameter', {'uom': 'in'}).text = header_data.get('Rollerbit', '')

def add_measurement_data(root, header_data, parameter_data, data_rows):
    measurement = ET.SubElement(root, 'measurement')
    mwd = ET.SubElement(measurement, 'MeasurementWhileDrilling', {'gml:id': f"id_{header_data.get('ID', 'Unknown')}"})
    ET.SubElement(mwd, 'gml:name').text = header_data.get('ID', '')
    ET.SubElement(mwd, 'investigationTarget').text = 'Natural Ground'
    ET.SubElement(mwd, 'projectRef', {'xlink:href': '#p1'})
    ET.SubElement(mwd, 'samplingFeatureRef', {'xlink:href': f"#id_{header_data.get('BoreholeID', 'Unknown')}"})
    
    add_mwd_result(mwd, parameter_data, data_rows)

def add_mwd_result(mwd, parameter_data, data_rows):
    outcome = ET.SubElement(mwd, 'outcome')
    result = ET.SubElement(outcome, 'MWDResult', {'gml:id': 'm1'})
    
    add_time_domain(result, data_rows)
    add_results(result, parameter_data, data_rows)

def add_time_domain(result, data_rows):
    time_domain = ET.SubElement(result, 'timeDomain')
    time_position_list = ET.SubElement(time_domain, 'TimePositionList', {'gml:id': 'tpl'})
    positions = ET.SubElement(time_position_list, 'timePositionList')
    # Join all timestamps with a space and wrap every 5 timestamps
    timestamps = [row[0] for row in data_rows]
    wrapped_timestamps = [' '.join(timestamps[i:i+5]) for i in range(0, len(timestamps), 5)]
    positions.text = '\n                '.join(wrapped_timestamps)

def add_results(result, parameter_data, data_rows):
    results = ET.SubElement(result, 'results')
    result_set = ET.SubElement(results, 'ResultSet')
    
    add_parameters(result_set, parameter_data)
    add_data_values(result_set, data_rows)

def add_parameters(result_set, parameter_data):
    parameters = ET.SubElement(result_set, 'parameters')
    property_params = ET.SubElement(parameters, 'PropertyParameters', {'gml:id': 'params1'})
    properties = ET.SubElement(property_params, 'properties')

    parameter_names = parameter_data['parameter_names']
    parameter_units = parameter_data['parameter_units']

    property_classes = {
        'Depth': 'measured_depth',
        'RateOfPenetration': 'penetration_rate',
        'RotationShaft': 'rotation_shaft',
        'RotationTool': 'rotation_tool',
        'Flow': 'fluid_injection_volume_rate',
        'PressureFlush': 'fluid_injection_pressure',
        'PressurePulldown': 'crowd_pressure',
        'RotationTach': 'rotation_tach',
        'TorqueTach': 'torque_tach',
        'Gear': 'gear_number',
        'AugerOD': 'auger_od',
        'RockCoreSize': 'core_size',
        'StopDepth': 'stop_depth',
    }

    index = 1
    for name, unit in zip(parameter_names, parameter_units):
        if name == 'Datum':
            continue  # Skip the Datum property

        property_element = ET.SubElement(properties, 'Property', {
            'gml:id': f'prop{index}',
            'index': str(index)
        })
        ET.SubElement(property_element, 'propertyName').text = name
        ET.SubElement(property_element, 'typeData').text = 'double'
        
        property_class = property_classes.get(name, 'missing')
        ET.SubElement(property_element, 'propertyClass', {
            'codeSpace': 'http://diggsml.org/def/codes/DIGGS/0.1/mwd_properties.xml'
        }).text = property_class
        
        if unit != '-':
            ET.SubElement(property_element, 'uom').text = unit
        
        ET.SubElement(property_element, 'nullValue', {'reason': 'missing'}).text = '9999'

        index += 1
def add_data_values(result_set, data_rows):
    data_values = ET.SubElement(result_set, 'dataValues', {'cs': ',', 'ts': ' ', 'decimal': '.'})
    data_value_rows = []
    for row in data_rows:
        data_value_row = ','.join(row[1:])  # Exclude the Datum column
        data_value_rows.append(data_value_row)
    data_values.text = '\n'.join(data_value_rows)


def main(input_file_path, output_file_path):

    header_data, parameter_data, data_rows = parse_input_file(input_file_path)
    

    root = create_diggs_xml(header_data, parameter_data, data_rows)

    # Convert the XML to a pretty-printed string
    xml_string = minidom.parseString(ET.tostring(root)).toprettyxml(indent='  ')

    # Write the XML to the output file
    with open(output_file_path, 'w') as file:
        file.write(xml_string)

if __name__ == "__main__":
    input_file = "/workspaces/MWD_Measurment_While_Drilling/updated_3-11-24.guh"
    output_file = "/workspaces/MWD_Measurment_While_Drilling/mwd_diggs.xml"
    main(input_file, output_file)