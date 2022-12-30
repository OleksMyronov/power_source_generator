from PyLTSpice.LTSpiceBatch import SimCommander
from PyLTSpice.LTSpice_RawRead import LTSpiceRawRead
import random
import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz
import re
import os
import argparse

#Some common nominal raw series for electronic components
E6_RAW  = np.array([100, 150, 220, 330, 470, 680])

E12_RAW = np.array([100, 120, 150, 180, 220, 270,
                    330, 390, 470, 560, 680, 820])

E24_RAW = np.array([100, 110, 120, 130, 150, 160, 180, 200,
                    220, 240, 270, 300, 330, 360, 390, 430,
                    470, 510, 560, 620, 680, 750, 820, 910])

E48_RAW = np.array([100, 105, 110, 115, 121, 127, 133, 140, 147, 154,
                    162, 169, 178, 187, 196, 205, 215, 226, 237, 249,
                    261, 274, 287, 301, 316, 332, 348, 365, 383, 402,
                    422, 442, 464, 487, 511, 536, 562, 590, 619, 649,
                    681, 715, 750, 787, 825, 866, 909, 953])

#Different component raws, common for LTSpice circuits
RAW_SERIES = {'ind':  E24_RAW,
              'ind2': E24_RAW,
              'cap':  E12_RAW,
              'res':  E48_RAW }

# Common resistor power nominal raw
R_POWER_RAW = np.array([0.125, 0.25, 0.5, 1.0, 2.0, 5.0,
                        10.0, 25.0, 50.0, 100.0])

# Common capacitor voltage nominal raw
C_VOLTAGE_RAW = np.array([10, 16, 20, 25, 35, 50, 63, 80,
                          100, 160, 200, 250, 350, 400, 450])

def number_to_nominal(number, series):
    '''Rounds number to nearest upper value in nominal series'''
    max_val = max(series) 
    raw_value = series[(series - number)>0]
    return raw_value[0] if number<max_val else number

def number_to_raw_value(number, raw = E48_RAW):
    '''Rounds first three number digits to nearest (upper or lower) value in series'''
    exp_number = "{:e}".format(number)
    value = exp_number.split('e')[0]
    dec = int(exp_number.split('e')[1])
    raw_value = raw[np.argmin(abs(raw - float(value)*100))]
    return float(raw_value*10**(dec-2))

def number_to_exp(number):
    '''Converts number to exponential abbreviated format like 10K or 47µ'''
    power_dict = {-5: 'f',
                  -4: 'p',
                  -3: 'n',
                  -2: 'µ',
                  -1: 'm',
                   0: '',
                   1: 'K',
                   2: 'Meg',
                   3: 'G'}
    exp_number = "{:e}".format(number)
    value = float(exp_number.split('e')[0])
    dec = exp_number.split('e')[1]
    power = int(dec)//3
    rem = int(dec)%3
    return str(round(value*10**rem, 1))+power_dict[power]

def exp_to_number(string):
    '''Converts exponential abbreviated number like 10K or 47µ to float format''' 
    ext_dict = {'f': 'e-15',
                'p': 'e-12',
                'n': 'e-9',
                'µ': 'e-6',
                'm': 'e-3',
                'k': 'e3',
                'K': 'e3',
                'Meg': 'e6',
                'G': 'e9'}
    for key, value in ext_dict.items():
        string = string.replace(key, value)
    return float(string)

def get_capacitor_nodes(filename, capacitor_name):
    '''Finds node names, connected to capacitor in LTSpice netlist file''' 
    nodes = None
    netlist_name = '.'.join(filename.split('.')[0:-1])+'_1.net'
    netlist_file = open(netlist_name, 'r')
    netlist = netlist_file.readlines()
    netlist_file.close()
    for line in netlist:
        if line.split()[0] == capacitor_name:
            nodes = (line.split()[1], line.split()[2])
    return nodes

def get_netlist_components(filename):
    '''Creates component values and component types dictionaries from .asc file'''
    components_dict = {}
    comp_types_dict = {}
    last_component_name = None
    component_type = None
    netlist_file = open(filename, 'r')
    for line in netlist_file:
        line = line.split()
        if line[0] == 'SYMBOL':
            component_type = line[1]
            last_component_name = ''
        if line[0] == 'SYMATTR' and line[1] == 'InstName':
            last_component_name = line[2]
        if (line[0] == 'SYMATTR') and (line[1] == 'Value'):
            if last_component_name != '' and (component_type in RAW_SERIES.keys()):
                if not ('Rload' in last_component_name):
                    components_dict.update({last_component_name: exp_to_number(line[2])})
                    comp_types_dict.update({last_component_name: component_type})
                    last_component_name = '' 
    netlist_file.close()
    return (components_dict, comp_types_dict)

def write_netlist_components(source_file, destination_file, components):
    '''Writes component dictionary to LTSpice .asc file, using source file as template'''
    netlist_file = open(source_file, 'r')
    netlist = netlist_file.readlines()
    netlist_file.close()
    last_component_name = ''
    for i in range(len(netlist)):
        line = netlist[i]
        keywords = line.split()
        if keywords[0] == 'SYMATTR':
            if keywords[1]== 'InstName' and keywords[2] in components.keys():
                last_component_name = keywords[2]
            if keywords[1]=='Value' and last_component_name!='':
                new_value = number_to_exp(components[last_component_name])
                netlist[i] = 'SYMATTR Value '+new_value+'\n'
                last_component_name = ''
    file = open(destination_file, 'w+')
    file.writelines(netlist)
    file.close()
    return

def get_voltage_source(file, node_patterns = ['IN', 'VIN']):
    '''Finds name of voltage source, connected to input node in .asc file'''
    input_voltage_name, node_name = None, None
    LTC = SimCommander(file)
    net_file_name = '.'.join(file.split('.')[0:-1])+'.net'
    netlist_file = open(net_file_name, 'r')
    netlist = netlist_file.readlines()
    netlist_file.close()
    input_voltage_node_name = ''
    for line in netlist:
        line = line.split()
        if len(line)>2:
            if line[1] in node_patterns or line[2] in node_patterns:
                input_voltage_name = line[0]
                node_name = line[1]
    return input_voltage_name, node_name

def write_intital_voltage(sourse_file, destination_file, voltage):
    '''Writes new input voltage source value to .asc file'''
    netlist_file = open(sourse_file, 'r')
    netlist = netlist_file.readlines()
    netlist_file.close()
    input_v_name, _ = get_voltage_source(sourse_file)
    last_component_name = ''
    for i in range(len(netlist)):
        line = netlist[i].split()
        if line[0] == 'SYMATTR' and line[1] == 'InstName' and line[2]==input_v_name:
            last_component_name = 'IN'    
        if (line[0] == 'SYMATTR') and (line[1] == 'Value') and (last_component_name == 'IN'):
            netlist[i] = 'SYMATTR Value '+ str(voltage) +'\n'
            last_component_name = ''  
    file = open(destination_file, 'w+')
    file.writelines(netlist)
    file.close()
    return

def mutation(parent, component_types, mutation_rate=0.1):
    '''Simple mutation function, randimly changes parent value by mutation_rate,
    then rounds result to nominal series raw for specific component'''
    child = {}
    for key, value in parent.items():
        mu = float(value)
        new_val = random.normalvariate(mu, mu*mutation_rate)
        raw = RAW_SERIES[component_types[key]]
        child.update({key: number_to_raw_value(new_val, raw)})
    return child

def crossover(parent1, parent2):
    '''Simple crossover function, randimly samples values from two parents'''    
    child = {}
    for key, value in parent1.items():
        new_value = random.choice([parent1[key], parent2[key]])
        child.update({key: new_value})
    return child

def generate_population(template, component_types, n=20):
    '''Generates initial population with n samples by template mutation''' 
    population = []
    population.append(template) #first sample is original
    for i in range(0,n-1):
        population.append(mutation(template, component_types))
    return population, component_types

def selection(population, filename, out_node_list=["V(OUT)"], v_out = [5], fraction=0.2):
    '''Performs selection of samples with the best fitness function values'''
    LTC = SimCommander(filename)
    LTC.set_parameters()
    for sample in population:
        for key, value in sample.items():
            LTC.set_component_value(key, value)   
        LTC.run() 
        LTC.wait_completion()
    fitness_scores = []
    n = len(population)
    for i in range(n):
        file = '.'.join(filename.split('.')[0:-1])+'_'+str(i+1)
        LTR = LTSpiceRawRead(file+'.raw')
        v_out_simulated = []
        for out_node in out_node_list:
            v_out_simulated.append(LTR.get_trace(out_node)[-1])
        #remove LTSpice simulation files
        for i in ['.raw', '.op.raw', '.log', '.net']: 
            if os.path.exists(file + i):
                os.remove(file + i)   
        fitness = (sum((np.array(v_out_simulated)-np.array(v_out))**2))**0.5
        fitness_scores.append(fitness)
    level = np.quantile(fitness_scores, fraction)
    print('Selection level: {}'.format(level))
    selected_scemes = [population[i] for i in range(n) if fitness_scores[i]<=level]
    best_scheme = population[np.argmin(fitness)]
    return selected_scemes, best_scheme, level

def create_new_generation(population_tuple, filename, out_node, new_vout, deviation):
    '''Performs selection-crossover-mutation'''
    generated = []
    population, component_types = population_tuple
    selected, best, level = selection(population, filename, out_node, new_vout)
    for i in range(0, len(population)-len(selected)):
        [p1, p2] = random.sample(selected, 2)
        c = mutation(crossover(p1, p2), component_types, deviation)
        generated.append(c)
    selected.extend(generated)
    return (selected, component_types), best, level

def output_relevance(desired_voltage, real_voltage):
    '''Defines how close are desired and real output voltages'''
    desired_voltage = sorted(desired_voltage)
    real_voltage = sorted(str_to_float_list(real_voltage))
    sd = (sum((np.array(desired_voltage)-np.array(real_voltage))**2))**0.5
    max_voltage = max([abs(x) for x in real_voltage])
    res = (max_voltage + 1)/(max_voltage + sd + 1)
    return 1 if desired_voltage==0 else res

def input_relevance(desired_voltage, real_voltage):
    '''Defines how close are desired and real input voltage'''
    res = (min(abs(real_voltage), desired_voltage)+1)/(max(abs(real_voltage), desired_voltage)+1)
    return 1 if desired_voltage==0 else res
    
def str_to_str_list(x):
    '''Function for unpacking multiple output node names from single .csv string'''
    x = x[1:-1]
    x = x.split(',')
    x = [i.strip() for i in x]
    return [i[1:-1] for i in x]

def str_to_float_list(x):
    '''Function for unpacking multiple output node values from single .csv string'''
    x = x[1:-1]
    x = x.split(',')
    x = [i.strip() for i in x]
    return [float(i) for i in x]

def get_best_scheme_match(request, database_file = 'Power_supply_data.csv'):
    '''Finds circuit from database_file, that "best matches" request text'''
    input_voltage = '0'
    output_voltage = '0'
    request = request.lower()
    requested = re.search(r'([0-9\.]*)v to ([0-9\.]*)v', request)
    if requested:
        if requested.group(1)!='' and requested.group(2)!='':
            request = re.sub(r'[0-9\.]*v to [0-9\.]*v ?', '', request)
            input_voltage = requested.group(1)
            output_voltage = requested.group(2)
    v_in_patterns = [r'([0-9\.]*)v input ?',
                     r'input ([0-9\.]*)v ?'
                     ]
    v_out_patterns = [r'output ([0-9\.]*)v and ([0-9\.]*)v ?',
                      r'output ([0-9\.]*)v, ([0-9\.]*)v ?',
                      r'([0-9\.]*)v and ([0-9\.]*)v output ?',
                      r'([0-9\.]*)v, ([0-9\.]*)v output ?',
                      r'([0-9\.]*)v output ?',
                      r'output ([0-9\.]*)v ?',
                     ]
    ac_input_patterns = [r'([0-9\.]*)v ?([0-9\.]*hz)? ac input ?',
                         r'ac input ([0-9\.]*)v ?([0-9\.]*hz)?',
                         r'input ac ([0-9\.]*)v ?([0-9\.]*hz)?',
                         r'input ([0-9\.]*)v ?([0-9\.]*hz)? ac',
                         ]
    ac_source = False
    input_frequency = 50
    for pattern in ac_input_patterns:
        requested = re.search(pattern, request)
        if requested:
            if requested.group(0)!='':
                ac_source = True
                input_voltage = requested.group(1)
                if requested.group(2):
                    input_frequency = requested.group(2)[:-2]
                request = re.sub(pattern, '', request)
    for pattern in v_in_patterns:
        requested = re.search(pattern, request)
        if requested:
            if requested.group(1)!='':
                input_voltage = requested.group(1)
                request = re.sub(pattern, '', request)
    output_voltage = []
    for pattern in v_out_patterns:
        requested =  re.findall(pattern, request)
        if requested:
            output_voltage = re.findall(pattern, request)[0]
            request = re.sub(pattern, '', request)
    if isinstance(output_voltage, str):
        output_voltage = [output_voltage]
    input_frequency = float(input_frequency)            
    input_voltage = float(input_voltage)
    if ac_source:
        input_voltage = round(1.41 * input_voltage, 1)
        ac_input = (input_voltage, input_frequency)
    else:
        ac_input = (None, None)       
    output_voltage = [float(x) for x in output_voltage]
    df = pd.read_csv(database_file, sep = ';').dropna()
    df = df[df['output_number']==len(output_voltage)]
    df['token_set_ratio'] = df['description'].map(lambda x: fuzz.token_sort_ratio(request, x))
    df['vin_relevance'] = df['input_voltage'].map(lambda x: input_relevance(input_voltage, x))
    df['vout_relevance'] = df['output_voltage'].map(lambda x: output_relevance(output_voltage, x))
    df['total_match_score'] = df['token_set_ratio'] + df['vin_relevance']*50 + df['vout_relevance']*50
    best_match = df.loc[df['total_match_score'].idxmax()]
    if input_voltage == 0:
        input_voltage = best_match['input_voltage']  
    print('AC input: {}'.format(ac_input))
    print('Input voltage: {}'.format(input_voltage))
    print('Output voltage: {}'.format(output_voltage))
    return best_match, input_voltage, output_voltage, ac_input

def write_component_additional_features(filename):
    '''Writes resistor thermal power, capacitor maximum voltage
    and inductance maximum current to LTSpice .asc file
    Initial file would be overwritten'''
    last_component_name = None
    component_type = None
    LTC = SimCommander(filename)
    LTC.set_parameters()
    LTC.run()
    LTC.wait_completion()
    rewrited_netlist = []
    netlist_file = open(filename, 'r')
    netlist = netlist_file.readlines()
    netlist_file.close()
    LTR = LTSpiceRawRead('.'.join(filename.split('.')[0:-1])+'_1.raw')
    for i in range(len(netlist)):
        line = netlist[i]
        if not('SYMATTR SpiceLine' in line):
            rewrited_netlist.append(line)
        line = line.split()
        if line[0] == 'SYMBOL':
            component_type = line[1]
            last_component_name = ''
        if line[0] == 'SYMATTR' and line[1] == 'InstName':
            last_component_name = line[2]
        if (line[0] == 'SYMATTR') and (line[1] == 'Value'):
            if last_component_name != '':
                if (component_type == 'res') and (last_component_name != 'Rload'):
                    res_current = max(LTR.get_trace('I('+last_component_name+')'))
                    res_value = exp_to_number(line[2])
                    arr = np.array(LTR.get_trace('I('+last_component_name+')')[:])
                    res_power = res_value * max(arr*arr)
                    res_power = str(number_to_nominal(res_power, R_POWER_RAW))
                    rewrited_netlist.append('SYMATTR SpiceLine pwr='+res_power+' tol=2\n')
                    last_component_name = ''
                if (component_type == 'cap'):
                    node1, node2 = get_capacitor_nodes(filename, last_component_name)
                    v1 = np.array(LTR.get_trace('V('+node1+')')[:]) if node1!='0' else 0
                    v2 = np.array(LTR.get_trace('V('+node2+')')[:]) if node2!='0' else 0
                    cap_voltage = max(abs(v1-v2))
                    cap_voltage = str(number_to_nominal(cap_voltage, C_VOLTAGE_RAW))
                    rewrited_netlist.append('SYMATTR SpiceLine V='+cap_voltage+'\n')
                    last_component_name = ''
                if (component_type in ['ind', 'ind2']):
                    l_current = np.array(LTR.get_trace('I('+last_component_name+')')[:])
                    peak_current = str(round(max(abs(l_current)),3))
                    rewrited_netlist.append('SYMATTR SpiceLine Ipk='+peak_current+'\n')
                    last_component_name = ''
    file = open(filename, 'w+')
    file.writelines(rewrited_netlist)
    file.close()           
    return

def get_workspace_frame(netlist_text):
    '''Finds min and max netlist component coordinates'''
    min_x, min_y, max_x, max_y =  10000, 10000, -10000, -10000
    for line in netlist_text:
        line = line.split()
        if line[0] == 'SYMBOL':
            x = int(line[2])
            y = int(line[3])
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
        if line[0] == 'WIRE':
            x1 = int(line[1])
            y1 = int(line[2])
            x2 = int(line[3])
            y2 = int(line[4])            
            min_x, max_x = min(min_x, x1, x2), max(max_x, x1, x2)
            min_y, max_y = min(min_y, y1, y2), max(max_y, y1, y2)           
    return min_x, min_y, max_x, max_y

def add_circuit_module(source_text, destination_text,
                       old_node_name = 'IN',
                       new_node_name = 'IN',
                       ac_source = (None, None),
                       source_rename = '_1', alignment = 'LEFT'):
    '''Appends circuit netlist to other circuit netlist,
    Connection would be performed by nodes'''
    min_dx, min_dy, max_dx, max_dy = get_workspace_frame(destination_text)
    min_sx, min_sy, max_sx, max_sy = get_workspace_frame(source_text)
    ac_voltage, ac_frequency = ac_source
    DELTA = 128  # space between circuits in LTSpice 
    if alignment == 'LEFT':
        dx = min_dx - max_sx + min_sx - DELTA
        dy = min_dy - min_sy
    elif alignment == 'RIGHT':
        dx = max_dx - min_sx + DELTA
        dy = min_dy - min_sy
    else:
        dx = 0
        dy = 0
    output_lines = []
    for i in range(len(source_text)):
        line = source_text[i].split()
        if line[0] == 'SYMBOL':
            x1 = int(line[2])
            y1 = int(line[3])
            source_text[i] = 'SYMBOL {} {} {} {}\n'.format(line[1], x1+dx, y1+dy, line[4])
        if line[0] == 'WIRE':
            x1 = int(line[1])
            y1 = int(line[2])
            x2 = int(line[3])
            y2 = int(line[4])
            source_text[i] = 'WIRE {} {} {} {}\n'.format(x1+dx, y1+dy, x2+dx, y2+dy)
        if line[0] == 'FLAG':
            if line[3] == old_node_name:
                line[3] = new_node_name
            x1 = int(line[1])
            y1 = int(line[2])
            source_text[i] = 'FLAG {} {} {}\n'.format(x1+dx, y1+dy, line[3])
        if line[0] == 'SYMATTR' and line[1] == 'InstName':
            source_text[i] = 'SYMATTR InstName {}_1\n'.format(line[2])
        if ac_voltage and source_text[i] == 'SYMATTR Value SINE(0 310 50)\n':
                source_text[i] = 'SYMATTR Value SINE(0 {} {})'.format(ac_voltage, ac_frequency)
        if not line[0] in ['Version', 'SHEET', 'TEXT']:
            output_lines.append(source_text[i])
    if ac_frequency:       #replacing simulation time in destination circuit with one AC period
        for i in range(len(destination_text)):
            line = destination_text[i].split()
            if line[0] == 'TEXT' and line[-1]=='startup':
                line[-2] = str(round(1000/ac_frequency))+'m' 
                destination_text[i] = ' '.join(line)+'\n'
    return destination_text + output_lines

def delete_components(text_lines, component_names = None):
    '''Delete components from netlist text by list of component names'''
    output_text = ''
    if component_names:
        component_start = [i for i, x in enumerate(text_lines) if 'SYMBOL' in x]
        component_end = component_start+ [len(text_lines)]
        component_start = [0] + component_start
        component_lines = tuple(zip(component_start, component_end))
        for component in component_lines:
            component_text = ''.join(text_lines[component[0] : component[1]])
            for component_name, component_type in component_names:
                pattern = r'SYMBOL '+component_type +'[\S\s]+?\nSYMATTR InstName '\
                + component_name+'\nSYMATTR Value \S*\n'
                component_text = re.sub(pattern,'', component_text)    
            output_text = output_text + component_text
    return output_text.splitlines(True)

def combine_input_circuit(input_file, body_file, ac_source):
    '''Rewrites body file with adding netlist from input file'''
    source_file = os.path.join('rectifiers', input_file)
    input_voltage_name, node_name = get_voltage_source(body_file)
    file = open(body_file, 'r')
    destination_text = file.readlines()
    file.close()
    file = open(source_file, 'r')
    source_text = file.readlines()
    file.close()
    destination_text = delete_components(destination_text,
                                         [(input_voltage_name, 'voltage'),
                                          (input_voltage_name, 'VOLTAGE')])
    destination_text = add_circuit_module(source_text, destination_text,
                                          old_node_name = 'IN', new_node_name = node_name,
                                          ac_source = ac_source)
    file = open(body_file, 'w')
    file.writelines(destination_text)
    file.close()
    return

def generate_scheme_by_request(request, n_generations=6, n_samples=20):
    '''Selects scheme from dataset and performs genetic algorithm optimization'''
    MIN_SD = 0.025 #minimum standard deviation
    MAX_SD = 0.5   #maximum standard deviation
    scheme, req_vin, req_vout, ac_in = get_best_scheme_match(request)
    print('Selected chip: {}'.format(scheme['chip_name']))
    print(scheme['description'])
    model = scheme['model_file']
    req_vout = sorted(req_vout)
    scheme_out = str_to_float_list(scheme['output_voltage'])
    node_out = str_to_str_list(scheme['output_node'])
    scheme_out = sorted(zip(node_out, scheme_out), key = lambda x: x[1])
    node_out = [x[0] for x in scheme_out]
    scheme_out = [x[1] for x in scheme_out]
    print('Selected chip output voltages: {}'.format(scheme_out))
    print('Selected chip output nodes: {}'.format(node_out))
    dir_path = 'pcb_dataset'
    scheme_path = os.path.join(dir_path, model)
    if os.path.isfile(scheme_path):
        write_intital_voltage(scheme_path, model, req_vin)
        if ac_in[0]:
            ac_input_path = 'full_wave.asc'  #the most common rectifier scheme
            combine_input_circuit(ac_input_path, model, ac_in)  
        template, component_types = get_netlist_components(model)
        pop = generate_population(template, component_types, n_samples)
        sd = (sum((np.array(req_vout)-np.array(scheme_out))**2))**0.5
        deviation = min(MAX_SD, sd + MIN_SD)
        for i in range(n_generations):
            print('Generation: {}'.format(i))
            pop, best, level = create_new_generation(pop, model, node_out, req_vout, deviation)
            deviation = level/max(req_vout)+MIN_SD
            print('Deviation: {}'.format(deviation))
    gen_name = 'generated_'+scheme['chip_name']+'.asc'
    write_netlist_components(model, gen_name, best)
    write_component_additional_features(gen_name)
    file = scheme['model_file'][:-4]
    for i in ['.raw', '.op.raw', '.log', '.net']:
        if os.path.exists(file + i):
            os.remove(file + i)
        if os.path.exists(gen_name[:-4] + '_1' + i):
            os.remove(gen_name[:-4] + '_1' + i)
    if os.path.exists(gen_name[:-4] + '.net'):
        os.remove(gen_name[:-4] + '.net')
    return 

text1 = 'step down converter 27v input 500mA output 16V'       
text2 = 'low noise linear regulator 40V to 7.2V'                
text3 = 'capacitor charger with 8.6V input and 160V output'      
text4 = 'linear converter 230v 50Hz AC input, 500mA output 12V'
text5 = 'step down AC-DC converter 24v input 500mA output 16V'  
text6 = 'linear converter 36v input, output 10V and 5.5V'
text7 = 'synchronous step-down controller 70V input, output 4.2V and 15V'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='text_info')
    parser.add_argument('--req', dest='req', type=str, default = text4, help='Request text')
    parser.add_argument('--gen', dest='gen', type=int, default=3, help='Number of generations')
    parser.add_argument('--pop', dest='pop', type=int, default=20, help='Number of samples in population')
    args = parser.parse_args()
    generate_scheme_by_request(args.req, args.gen, args.pop)
