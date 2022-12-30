# Electronic circuit generator

This project is based on LTSpice circuit simulator. It uses ready-made power supply circuits from LTSpice library to create new power supply 
circuits with different component parameters and desired output voltages.

#### **!NOTE: Successful LTSpice simulation doesn't mean successful circuit operation in reality. Check that there is no temperature, voltage, current or other component parameter limits exceeded. Use manufacturer documentation for specific component to verify actual parameter limits.

## Installation
1. Clone this repo to your local machine

2. Install LTSpice XVII, [link](https://www.analog.com/en/design-center/design-tools-and-calculators/ltspice-simulator.html)

3. Install Python 3.9 (if required)

4. Install Python modules (if required):

    PyLTSpice>=2.3
    
    numpy>=1.21.6
    
    pandas>=1.1.5
    
    fuzzywuzzy>=0.18.0

## How to use:
  You can to use command line with arguments to launch algorithm
  **--req** - request text in string format, starting and ending with "
  **--gen** - positive integer number. Defines number of genetic algorithm generations
  **--pop** - positive integer number. Defines number of circuit samples in generation
  **--sel** - float number in range (0:1). Defines fraction of samples, selected for "breeding" in single generation

Example: 
python scheme_generator.py --req "step down converter 27v input, 500mA 16V output" --gen 6 --pop 20

Simulation might take a long time, alse there is no guarantee that algorithm would converge - some schemes have fixed parameters.
Results would be saved in script folder, original circuit with its original name and generated circuit with "generated_" prefix.
You can open this files with LTSpice, simulate and check results.
