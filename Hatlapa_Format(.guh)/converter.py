import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, date
import sys
import os
import traceback

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
    """
    Parses a .guh file and extracts header data, parameter data, and data rows
    with improved error handling.
    """
    header_data = {}
    parameter_data = {}
    data_rows = []

    try:
        with open(file_path, 'r') as file:
            section = None
            for line_num, line in enumerate(file, 1):
                try:
                    line = line.strip()
                    if line.startswith('[HEADER]'):
                        section = 'header'
                        print(f"Found HEADER section at line {line_num}")
                    elif line.startswith('[PARAMETER]'):
                        section = 'parameter'
                        print(f"Found PARAMETER section at line {line_num}")
                    elif line.startswith('[DATA]'):
                        section = 'data'
                        print(f"Found DATA section at line {line_num}")
                    elif line == '':
                        continue
                    else:
                        if section == 'header':
                            if '=' in line:
                                parts = line.split('=', 1)  # Split on first equals sign only
                                if len(parts) == 2:
                                    key, value = parts
                                    # Remove leading/trailing zeros for coordinate fields
                                    if key.strip() in ['Latitude_Modem', 'Longitude_Modem', 'Altitude_Modem']:
                                        value = value.lstrip('0') or '0'  # Keep at least one zero if all zeros
                                    header_data[key.strip()] = value.strip()
                        elif section == 'parameter':
                            if 'parameter_names' not in parameter_data:
                                parameter_data['parameter_names'] = line.split(';')
                                print(f"Parameter names: {parameter_data['parameter_names']}")
                            elif 'parameter_units' not in parameter_data:
                                parameter_data['parameter_units'] = line.split(';')
                                print(f"Parameter units: {parameter_data['parameter_units']}")
                        elif section == 'data':
                            if line.startswith('Datum'):
                                continue
                            row = line.split(';')
                            # Validate row has at least 2 elements before adding
                            if len(row) >= 2:
                                data_rows.append(row)
                            else:
                                print(f"Skipping invalid data row at line {line_num}: {line} (not enough columns)")
                except Exception as e:
                    print(f"Error processing line {line_num}: {str(e)}")
                    # Continue processing other lines
        
        # Validate we have parameter data
        if not parameter_data or 'parameter_names' not in parameter_data or 'parameter_units' not in parameter_data:
            print("Missing parameter data in file")
            raise ValueError("File is missing required parameter section")
            
        # Validate parameter names and units match in length
        if 'parameter_names' in parameter_data and 'parameter_units' in parameter_data:
            if len(parameter_data['parameter_names']) != len(parameter_data['parameter_units']):
                print(f"Parameter names and units length mismatch: "
                      f"{len(parameter_data['parameter_names'])} names vs "
                      f"{len(parameter_data['parameter_units'])} units")
                
                # Adjust to match the shorter length
                min_length = min(len(parameter_data['parameter_names']), len(parameter_data['parameter_units']))
                parameter_data['parameter_names'] = parameter_data['parameter_names'][:min_length]
                parameter_data['parameter_units'] = parameter_data['parameter_units'][:min_length]
        
        # Log data rows stats
        print(f"Parsed {len(data_rows)} data rows")
        if data_rows:
            print(f"First row: {data_rows[0]}")
            print(f"Last row: {data_rows[-1]}")
            print(f"Column count in first row: {len(data_rows[0])}")
            
    except Exception as e:
        print(f"Error parsing input file: {str(e)}")
        # Return empty but valid structures if parsing failed
        if not parameter_data:
            parameter_data = {'parameter_names': ['Datum', 'Depth'], 'parameter_units': ['-', 'm']}
        if not data_rows:
            data_rows = [['1900-01-01T00:00:00', '0.0']]

    return header_data, parameter_data, data_rows

def create_diggs_xml(header_data, parameter_data, data_rows):
    """
    Creates a DIGGS XML structure from parsed data.
    """
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
    add_sampling_feature(root, header_data, data_rows)

    # Add measurement data
    add_measurement_data(root, header_data, parameter_data, data_rows)

    return root

def add_document_information(root):
    """
    Adds document information to the DIGGS XML.
    """
    document_info = ET.SubElement(root, 'documentInformation')
    doc_info_element = ET.SubElement(document_info, 'DocumentInformation', {'gml:id': 'mwd_guh_2_DIGGS'})
    ET.SubElement(doc_info_element, 'creationDate').text = date.today().isoformat()

def add_project_information(root, header_data):
    """
    Adds project information to the DIGGS XML.
    """
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
    """
    Adds sampling feature information to the DIGGS XML.
    """
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
    add_construction_method(borehole, header_data, data_rows)

def add_reference_point(borehole, header_data):
    """
    Adds reference point information to the borehole.
    """
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
    """
    Adds center line information to the borehole with robust error handling.
    """
    center_line = ET.SubElement(borehole, 'centerLine')
    linear_extent = ET.SubElement(center_line, 'LinearExtent', {'gml:id': 'Linear_Extent_0'})
    pos_list = ET.SubElement(linear_extent, 'gml:posList', {
        'srsDimension': '3',
        'uomLabels': 'dega dega m',
        'axisLabels': 'latitude longitude height'
    })
    
    # Get coordinate values with defaults
    lat = header_data.get('Latitude_Modem', '0')
    lon = header_data.get('Longitude_Modem', '0')
    alt = header_data.get('Altitude_Modem', '0')
    
    # Create start depth coordinate
    start_depth = f"{lat} {lon} {alt}"
    
    # Safely calculate end depth
    try:
        # Check if we have data rows and if the last row has enough elements
        if data_rows and len(data_rows[-1]) > 1:
            # Get the depth value from the last row
            depth_value = data_rows[-1][1]
            print(f"Using depth value: {depth_value} from last row")
            
            # Convert to float and calculate end depth
            depth_float = float(depth_value)
            alt_float = float(alt)
            end_alt = -(alt_float - depth_float)
            end_depth = f"{lat} {lon} {end_alt}"
        else:
            # If no valid data, use a default end depth
            print("No valid data rows for depth calculation, using default end depth")
            end_depth = f"{lat} {lon} -10.0"  # Default 10m depth
    except (ValueError, IndexError) as e:
        # Handle conversion errors or index errors
        print(f"Error calculating end depth: {str(e)}, using default")
        end_depth = f"{lat} {lon} -10.0"  # Default 10m depth
    
    pos_list.text = f"{start_depth} {end_depth}"
    print(f"Center line positions: {start_depth} to {end_depth}")

def add_linear_referencing(borehole):
    """
    Adds linear referencing information to the borehole.
    """
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
    """
    Adds total measured depth information to the borehole with error handling.
    """
    try:
        # Check if we have data rows
        if not data_rows:
            print("No data rows available for total measured depth calculation")
            max_depth = 10.0  # Default 10m depth
        else:
            # Safely extract depth values
            valid_depths = []
            for i, row in enumerate(data_rows):
                try:
                    if len(row) > 1:
                        depth_value = float(row[1])
                        valid_depths.append(abs(depth_value))
                    else:
                        print(f"Row {i} doesn't have enough elements for depth: {row}")
                except (ValueError, IndexError) as e:
                    print(f"Error parsing depth in row {i}: {str(e)}")
            
            # Calculate max depth if we have valid values
            if valid_depths:
                max_depth = max(valid_depths)
                print(f"Calculated max depth: {max_depth}m from {len(valid_depths)} valid depths")
            else:
                print("No valid depths found, using default")
                max_depth = 10.0  # Default 10m depth
    except Exception as e:
        print(f"Error in add_total_measured_depth: {str(e)}")
        max_depth = 10.0  # Default 10m depth
    
    ET.SubElement(borehole, 'totalMeasuredDepth', {'uom': 'm'}).text = f'{max_depth:.2f}'

def add_casing(borehole, header_data):
    """
    Adds casing information to the borehole.
    """
    try:
        casing = ET.SubElement(borehole, 'casing')
        casing_element = ET.SubElement(casing, 'Casing', {'gml:id': f"id_{header_data.get('BoreholeID', 'Unknown')}_casing1"})
        ET.SubElement(casing_element, 'casingOutsideDiameter', {'uom': 'in'}).text = header_data.get('CasingOD(inch)', '')
    except Exception as e:
        print(f"Error in add_casing: {str(e)}")

def add_construction_method(borehole, header_data, data_rows):
    """
    Adds construction method information to the borehole with error handling.
    """
    construction_method = ET.SubElement(borehole, 'constructionMethod')
    method_element = ET.SubElement(construction_method, 'BoreholeConstructionMethod', {'gml:id': f"{header_data.get('BoreholeID', 'Unknown')}_cons_method1"})
    ET.SubElement(method_element, 'gml:name').text = 'Auger'
    
    # Add location element
    location = ET.SubElement(method_element, 'location')
    linear_extent = ET.SubElement(location, 'LinearExtent', {'gml:id': f"{header_data.get('BoreholeID', 'Unknown')}_cons_method1_le"})
    
    # Calculate total depth safely
    try:
        if not data_rows:
            print("No data rows available for construction method depth calculation")
            total_depth = 10.0  # Default 10m depth
        else:
            # Safely extract depth values
            valid_depths = []
            for i, row in enumerate(data_rows):
                try:
                    if len(row) > 1:
                        depth_value = float(row[1])
                        valid_depths.append(abs(depth_value))
                except (ValueError, IndexError) as e:
                    print(f"Error parsing depth in row {i} for construction method: {str(e)}")
            
            # Calculate max depth if we have valid values
            if valid_depths:
                total_depth = max(valid_depths)
            else:
                print("No valid depths found for construction method, using default")
                total_depth = 10.0  # Default 10m depth
    except Exception as e:
        print(f"Error in construction method depth calculation: {str(e)}")
        total_depth = 10.0  # Default 10m depth
    
    pos_list = ET.SubElement(linear_extent, 'gml:posList', {'srsName': '#lrs', 'srsDimension': '1'})
    pos_list.text = f"0 {total_depth:.2f}"
    
    add_construction_equipment(method_element, header_data)

def add_construction_equipment(method_element, header_data):
    """
    Adds construction equipment information to the method element.
    """
    try:
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
        try:
            if '=' in rock_core_size:
                ET.SubElement(coring_device, 'barrelInnerDiameter', {'uom': 'in'}).text = rock_core_size.split('=')[-1].strip()
            else:
                ET.SubElement(coring_device, 'barrelInnerDiameter', {'uom': 'in'}).text = rock_core_size
        except Exception as e:
            print(f"Error processing rock core size: {str(e)}")
            ET.SubElement(coring_device, 'barrelInnerDiameter', {'uom': 'in'}).text = '0'
    except Exception as e:
        print(f"Error in add_construction_equipment: {str(e)}")

def parse_client_info(client_info):
    """
    Parses client information into make and model with error handling.
    """
    try:
        # Ensure client_info is a string
        if not isinstance(client_info, str):
            print(f"Client info is not a string: {client_info}")
            return "Unknown", "Unknown"
            
        # Attempt to split the client info into make and model
        parts = client_info.split()
        if len(parts) >= 2:
            make = parts[0]
            model = ' '.join(parts[1:])
        else:
            make = client_info
            model = "Unknown"
        return make, model
    except Exception as e:
        print(f"Error parsing client info: {str(e)}")
        return "Unknown", "Unknown"

def add_cutting_tool_info(drill_rig, header_data):
    """
    Adds cutting tool information to the drill rig with error handling.
    """
    try:
        cutting_tool_info = ET.SubElement(drill_rig, 'cuttingToolInfo')
        
        auger_tool = ET.SubElement(cutting_tool_info, 'CuttingTool')
        ET.SubElement(auger_tool, 'gml:name').text = 'Auger'
        ET.SubElement(auger_tool, 'toolOuterDiameter', {'uom': 'in'}).text = header_data.get('AugerID', '')
        
        roller_bit_tool = ET.SubElement(cutting_tool_info, 'CuttingTool')
        ET.SubElement(roller_bit_tool, 'gml:name').text = 'Roller bit'
        ET.SubElement(roller_bit_tool, 'toolOuterDiameter', {'uom': 'in'}).text = header_data.get('Rollerbit', '')
    except Exception as e:
        print(f"Error in add_cutting_tool_info: {str(e)}")

def add_measurement_data(root, header_data, parameter_data, data_rows):
    """
    Adds measurement data to the DIGGS XML.
    """
    try:
        measurement = ET.SubElement(root, 'measurement')
        mwd = ET.SubElement(measurement, 'MeasurementWhileDrilling', {'gml:id': f"id_{header_data.get('ID', 'Unknown')}"})
        ET.SubElement(mwd, 'gml:name').text = header_data.get('ID', '')
        ET.SubElement(mwd, 'investigationTarget').text = 'Natural Ground'
        ET.SubElement(mwd, 'projectRef', {'xlink:href': '#p1'})
        ET.SubElement(mwd, 'samplingFeatureRef', {'xlink:href': f"#id_{header_data.get('BoreholeID', 'Unknown')}"})
        
        add_mwd_result(mwd, parameter_data, data_rows)
    except Exception as e:
        print(f"Error in add_measurement_data: {str(e)}")

def add_mwd_result(mwd, parameter_data, data_rows):
    """
    Adds MWD result information to the MWD element.
    """
    try:
        outcome = ET.SubElement(mwd, 'outcome')
        result = ET.SubElement(outcome, 'MWDResult', {'gml:id': 'm1'})
        
        add_time_domain(result, data_rows)
        add_results(result, parameter_data, data_rows)
    except Exception as e:
        print(f"Error in add_mwd_result: {str(e)}")

def add_time_domain(result, data_rows):
    """
    Adds time domain information to the result with error handling.
    """
    time_domain = ET.SubElement(result, 'timeDomain')
    time_position_list = ET.SubElement(time_domain, 'TimePositionList', {'gml:id': 'tpl'})
    positions = ET.SubElement(time_position_list, 'timePositionList')
    
    try:
        # Safely extract timestamps
        timestamps = []
        for i, row in enumerate(data_rows):
            try:
                if row and len(row) > 0:
                    # Validate timestamp format
                    timestamp = row[0].strip()
                    timestamps.append(timestamp)
                else:
                    print(f"Row {i} doesn't have a timestamp: {row}")
                    # Add a placeholder timestamp
                    timestamps.append(f"1900-01-01T00:00:{i:02d}")
            except IndexError:
                print(f"Error accessing timestamp in row {i}")
                # Add a placeholder timestamp
                timestamps.append(f"1900-01-01T00:00:{i:02d}")
        
        print(f"Extracted {len(timestamps)} timestamps")
        
        # Join all timestamps with a space and wrap every 5 timestamps
        if timestamps:
            wrapped_timestamps = [' '.join(timestamps[i:i+5]) for i in range(0, len(timestamps), 5)]
            positions.text = '\n                '.join(wrapped_timestamps)
        else:
            # If no timestamps, add a default
            print("No valid timestamps, using default")
            positions.text = "1900-01-01T00:00:00"
    except Exception as e:
        print(f"Error in add_time_domain: {str(e)}")
        # Set a default timestamp
        positions.text = "1900-01-01T00:00:00"

def add_results(result, parameter_data, data_rows):
    """
    Adds results information to the result.
    """
    try:
        results = ET.SubElement(result, 'results')
        result_set = ET.SubElement(results, 'ResultSet')
        
        add_parameters(result_set, parameter_data)
        add_data_values(result_set, data_rows)
    except Exception as e:
        print(f"Error in add_results: {str(e)}")

def add_parameters(result_set, parameter_data):
    """
    Adds parameters information to the result set with error handling.
    """
    try:
        parameters = ET.SubElement(result_set, 'parameters')
        property_params = ET.SubElement(parameters, 'PropertyParameters', {'gml:id': 'params1'})
        properties = ET.SubElement(property_params, 'properties')

        if 'parameter_names' not in parameter_data or 'parameter_units' not in parameter_data:
            print("Missing parameter_names or parameter_units in parameter_data")
            parameter_names = ['Depth']
            parameter_units = ['m']
        else:
            parameter_names = parameter_data['parameter_names']
            parameter_units = parameter_data['parameter_units']
            
            # Ensure equal lengths
            if len(parameter_names) != len(parameter_units):
                print("Parameter names and units have different lengths, adjusting...")
                min_len = min(len(parameter_names), len(parameter_units))
                parameter_names = parameter_names[:min_len]
                parameter_units = parameter_units[:min_len]

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
        for i, (name, unit) in enumerate(zip(parameter_names, parameter_units)):
            try:
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
            except Exception as e:
                print(f"Error adding parameter {name}: {str(e)}")
    except Exception as e:
        print(f"Error in add_parameters: {str(e)}")

def add_data_values(result_set, data_rows):
    """
    Adds data values to the result set with error handling.
    """
    data_values = ET.SubElement(result_set, 'dataValues', {'cs': ',', 'ts': ' ', 'decimal': '.'})
    data_value_rows = []
    
    try:
        for i, row in enumerate(data_rows):
            try:
                if len(row) > 1:
                    # Get values excluding Datum column
                    values = row[1:]
                    data_value_row = ','.join(values)
                    data_value_rows.append(data_value_row)
                else:
                    print(f"Row {i} has insufficient data: {row}")
                    # Add a default row with zeroes
                    num_columns = len(data_rows[0][1:]) if data_rows and len(data_rows[0]) > 1 else 1
                    data_value_rows.append(','.join(['0.0'] * num_columns))
            except Exception as e:
                print(f"Error processing data row {i}: {str(e)}")
        
        print(f"Processed {len(data_value_rows)} data value rows")
        
        if data_value_rows:
            data_values.text = '\n'.join(data_value_rows)
        else:
            # Default data if none available
            print("No valid data value rows, using default")
            data_values.text = "0.0,0.0"
    except Exception as e:
        print(f"Error in add_data_values: {str(e)}")
        # Set default data
        data_values.text = "0.0,0.0"

def main(input_file_path, output_file_path):
    """
    Main function to convert .guh file to DIGGS XML with enhanced error handling.
    """
    try:
        print(f"Starting conversion from {input_file_path} to {output_file_path}")
        
        # Check if input file exists
        if not os.path.exists(input_file_path):
            print(f"Error: Input file {input_file_path} does not exist")
            return False
            
        # Parse the input file
        print("Parsing input file...")
        header_data, parameter_data, data_rows = parse_input_file(input_file_path)
        
        print(f"Parsed file with {len(header_data)} header items, "
               f"{len(parameter_data.get('parameter_names', []))} parameters, "
               f"and {len(data_rows)} data rows")
        
        # Create DIGGS XML
        print("Creating DIGGS XML structure...")
        root = create_diggs_xml(header_data, parameter_data, data_rows)
        
        # Convert the XML to a pretty-printed string
        print("Converting XML to string...")
        try:
            xml_string = minidom.parseString(ET.tostring(root)).toprettyxml(indent='  ')
        except Exception as e:
            print(f"Error pretty-printing XML: {str(e)}")
            # Fallback to plain string conversion
            xml_string = ET.tostring(root, encoding='unicode')
        
        # Write the XML to the output file
        print(f"Writing XML to {output_file_path}...")
        with open(output_file_path, 'w') as file:
            file.write(xml_string)
        
        print("Conversion completed successfully")
        return True
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        traceback.print_exc()
        
        # Create a simple valid XML if conversion failed
        try:
            print("Creating fallback minimal DIGGS XML...")
            root = ET.Element('Diggs', {
                'xmlns': 'http://diggsml.org/schemas/2.6',
                'gml:id': 'Fallback_DIGGS'
            })
            
            doc_info = ET.SubElement(root, 'documentInformation')
            doc_element = ET.SubElement(doc_info, 'DocumentInformation', {'gml:id': 'fallback_doc'})
            ET.SubElement(doc_element, 'creationDate').text = date.today().isoformat()
            ET.SubElement(doc_element, 'comment').text = f"Error during conversion: {str(e)}"
            
            # Write minimal XML to file
            xml_string = ET.tostring(root, encoding='unicode')
            with open(output_file_path, 'w') as file:
                file.write(xml_string)
            
            print("Fallback DIGGS XML created")
            return True
        except Exception as fallback_error:
            print(f"Fallback XML creation failed: {str(fallback_error)}")
            
            # Last resort: Write error message as XML
            try:
                with open(output_file_path, 'w') as file:
                    file.write(f'<?xml version="1.0" ?>\n<DiggsFallback>\n  <error>{str(e)}</error>\n</DiggsFallback>')
                return True
            except:
                print("All attempts to create DIGGS file failed")
                return False

if __name__ == "__main__":
    if len(sys.argv) == 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        # Default paths if not provided as arguments
        input_file = "/workspaces/MWD_Measurment_While_Drilling/Hatlapa_Format(.guh)/updated_3-11-24.guh"
        output_file = "/workspaces/MWD_Measurment_While_Drilling/mwd_diggs.xml"
        print(f"Using default paths: {input_file} -> {output_file}")
        print("To specify paths: python converter.py <input_file> <output_file>")
    
    success = main(input_file, output_file)
    if success:
        print(f"Successfully created DIGGS XML file: {output_file}")
        sys.exit(0)
    else:
        print("Conversion failed")
        sys.exit(1)