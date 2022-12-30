# Electronic circuit generator

This project is based on LTSpice circuit simulator. It uses ready-made power supply circuits from LTSpice library to create new power supply 
circuits with different component parameters and desired output voltages. 

Project uses simple genetic algorithm to change circuit parameters. Algorithm performs mutation and crossover on values of resistors, capacitors and inductances, values of other more complicated components (like zener diods, transistors and chips) remains unchanged. Circuit topology also remains unchanged, except adding full-wave rectifier for transforming DC/DC converters to AC/DC. LTSpice simulator is used to check circuit validity, measure simulated voltages and define how well it matches the desired parameters.

Power source generator provides next functionality:

- selecting power supply circuit that best matches request and adjusting it to desired output parameters

- rounding up selected resistors to E48 nominal raw, capacitors to E12 raw, inductances to E24 raw

- calculating and writing to generated file resistor thermal power, capacitor maximum voltage and inductance maximum current. To see this parameters you should open generated scheme in LTSpice and open parameter window by right click on component. Resistor thermal power and capacitor maximum voltage are rounded up to common nominal raw.

- transforming DC/DC converters to AC/DC by adding full-wave rectifier circuit

- ajusting power supply circuits with two outputs. Althouhg algorithm is capable to ajust circuits with three and more outputs, 

### ***! NOTE

#### **Successful LTSpice simulation doesn't mean successful circuit operation in reality. Check that there is no temperature, voltage, current or other component parameter limits exceeded. Use manufacturer documentation for specific component to verify actual parameter limits.**

## Installation
1. Clone this repo to your local machine

2. Install LTSpice XVII, [link](https://www.analog.com/en/design-center/design-tools-and-calculators/ltspice-simulator.html)

3. Install Python 3.9 (if required)

4. Install Python modules (if required):
    PyLTSpice>=2.3, 
    numpy>=1.21.6, 
    pandas>=1.1.5, 
    fuzzywuzzy>=0.18.0
    
## How to use:
  You can to use command line with arguments to launch algorithm
  
  **--req** - request text in string format, starting and ending with "
  
  **--gen** - positive integer number. Defines number of genetic algorithm generations
  
  **--pop** - positive integer number. Defines number of circuit samples in generation
  
  **--sel** - float number in range (0:1). Defines fraction of samples, selected for "breeding" in single generation

Example: 

python scheme_generator.py --req "low noise linear regulator 40V to 7.2V" --gen 8 --pop 25 --sel 0.2

By default algorithm uses next arguments: 

req="step down converter 27v input, 500mA 16V output", gen=6, pop=20, sel=0.2

Simulation might take a long time, alse there is no guarantee that algorithm would converge - some schemes have fixed parameters.
Results would be saved in script folder, original circuit with its original name and generated circuit with "generated_" prefix.
You can open this files with LTSpice, simulate and check results.

## Parameters description

**--gen** defines number of genetic algorithm generations. More generations means more precise results, but also it would take proportionally more time for simulation.
It's recommended to start a trial simulation with 3-5 generations to determine if selected scheme converges to desired parameters and how much time is needed per single generation. 

**--pop** - defines number of circuit samples in generation. More samples means faster convergence but proportionally more simulation time.
For small circuits 20 samples is usually enouhg, for large circuits it's recommended to set this number at leas to component number.

**--sel** - defines fraction of samples, selected in single generation. pop\*sel should be at least 2 for successfull breeding. Small selection rate usually provides faster algorithm convergence, but less chances to get out from local optimum.



