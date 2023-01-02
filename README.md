# Electronic circuit generator

This project is based on LTSpice circuit simulator. It uses ready-made power supply circuits from LTSpice library to create new power supply 
circuits with different component parameters and desired output voltages.

The purpose of this project is to demonstrate the ability to optimize electronic circuit without prewious knowledge of how it actually works. Any power supply circuit has input voltage source and converts it to output. LTSpice simulator performs this conversion as a "black box" and genetic algorithm just operates with some abstract circuit features, comparing actual and desired outputs of different circuit variations.

Project uses simple genetic algorithm to change circuit parameters. Algorithm performs mutation and crossover on values of resistors, capacitors and inductances, values of other, more complicated components (like zener diods, transistors and chips) remains unchanged. Circuit topology also remains unchanged, except adding full-wave rectifier for transforming DC/DC converters to AC/DC. LTSpice simulator is used to check circuit validity, measure simulated output voltages and determine how well they match the desired parameters. Output load resistors also would remain unchanged. 

Power source generator provides next functionality:

- selecting power supply circuit that best matches text request and adjusting it to desired output parameters

- rounding up selected resistors to E48 nominal raw, capacitors to E12 raw, inductances to E24 raw

- calculating and writing to generated file resistor thermal power, capacitor maximum voltage and inductance maximum current. To see this parameters you should open generated scheme in LTSpice and open parameter window with right click on component. Resistor thermal power and capacitor maximum voltage are rounded up to common nominal raw.

- transforming DC/DC converters to AC/DC by adding full-wave rectifier circuit with AC source. AC source voltage RMS value and frequency should be defined in request.
AC voltage source would be simulated for 1/2 period, that is usually much more than original simulation time in LTSpice demo circuit, so total simulation time for AC/DC converter might be enormously long in compare with DC/DC converter.

- ajusting power supply circuits with two outputs. Althouhg algorithm is capable to ajust circuits with three and more outputs, most LTSpice multi-output chips have fixed output voltages and are not suitable for ajustment.

### **! NOTE**

#### **Successful LTSpice simulation doesn't mean successful circuit operation in reality. Check that there is no temperature, voltage, current or other component parameter limits exceeded. Use manufacturer documentation for specific component to verify actual parameter limits.**

**Most demo circuits in LTSpice database have low input voltage and chip VCC pin connected directly to input voltage source. Setting different, high input voltage to chip does't break the simulation. You may fix this manually, adding voltage divider or resistor with zener diode in LTSpice.**

For this project we use more than 1200 demo circuits from LTSpice database. It's also possible to optimize your own power supply circuit. You should add circuit .asc file to **pcb_dataset** folder and add your specific circuit description with basic parameters to **Power_supply.csv**. Then just add your description and new desired parameters to your request. Expanding circuit dataset would improve functionality.

## Installation
1. Clone this repo to your local machine

2. Install LTSpice XVII, [link](https://www.analog.com/en/design-center/design-tools-and-calculators/ltspice-simulator.html)

3. Install Python 3.9

4. Install Python modules:
    PyLTSpice>=2.3, 
    numpy>=1.21.6, 
    pandas>=1.1.5, 
    fuzzywuzzy>=0.18.0
    
## How to use:
  You can launch algorithm script **scheme_generator.py** from command line with arguments
  
  **--req** - request text in string format, starting and ending with "
  
  **--gen** - positive integer number. Defines number of genetic algorithm generations
  
  **--pop** - positive integer number. Defines number of circuit samples in generation
  
  **--sel** - float number in range (0:1). Defines fraction of samples, selected for breeding in generation

Example: 

python scheme_generator.py --req "low noise linear regulator 40V to 7.2V" --gen 8 --pop 25 --sel 0.2

By default algorithm uses next arguments: 

req="step down converter 27v input, 500mA 16V output"

gen=6

pop=20

sel=0.2

Simulation might take a long time, also there is no guarantee that algorithm would converge - some schemes have fixed parameters.
Results would be saved in script folder: original circuit with its original name and generated circuit with "generated_" prefix.
You can open this files with LTSpice, simulate and check the result.

## Parameters description

**--gen** defines number of genetic algorithm generations. More generations means more precise results, but also it would take proportionally more time for simulation.
It's recommended to start a trial simulation with 2-5 generations to determine if selected scheme converges to desired parameters and how much time is needed per single generation. 

**--pop** - defines number of circuit samples in generation. More samples means faster convergence but proportionally more simulation time.
For small circuits 20 samples is usually enouhg, for large circuits it's recommended to set this number to at leas component number.

**--sel** - defines fraction of samples, selected in single generation. pop\*sel should be at least 2 for successfull breeding. Small selection rate usually provides faster algorithm convergence, but less chances to get out from local optimum.



