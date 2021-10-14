import itertools, json
import pandas as pd

"""
    Author: Joseph Langford
    Creation Date: 10-12-2021
    
    Instructions: Respec your Attribute Points with your armor and weapons attached, fill out the  

    Description: A tool designed to allow New World players to enter their character information and find the best possible Attribute Point combination \
        for their current build at their level. Notes below:
    
    NOTES:
        Most of the information comes from this video:
        https://youtu.be/CxC_Vn31ibI?t=135
        However, the correct formula is
        Base dmg * (Scaling + Attributes) = Dmg
        Scaling = 2.5 * (level-1)
        Number at the top includes scaling for attributes, player level (2.5% per level)
        Weapons with 1 attribute scale per level sections
        ---------------------------------------------------
        0-100:   16.25 per 10 / point x 100 -> max: 162.5 % 
        101-150: 13.0 per 10  / point x 50  -> max: 65.0   %
        151-200: 11.7 per 10  / point x 50  -> max: 58.5   %
        201-250: 10.4 per 10  / point x 50  -> max: 52.0   %
        251-300: 9.1 per 10   / point x 50  -> max: 45.5   % 
        301+:    7.8 per 10   / point x 

        Weapons with 2 attribute scale per level sections (primary) (0.9 times single attribute scaling)
        -----------------------------------------------------------------
        0-100:   14.63 / point x 100 -> max: 146.25 % 
        101-150: 11.7  / point x 50  -> max: 58.50  %
        151-200: 10.53 / point x 50  -> max: 52.65  %
        201-250: 9.36  / point x 50  -> max: 46.80  %
        251-300: 8.19  / point x 50  -> max: 40.95  % 
        301+:    7.02  / point x x

        Weapons with 2 attribute scale per level sections (secondary) (0.65 times single attribute scaling)
        --------------------------------------------------------------------
        0-100:   10.56 / point x 100 -> max: 105.63 % 
        101-150: 8.45  / point x 50  -> max: 42.25  %
        151-200: 7.61  / point x 50  -> max: 38.03  %
        201-250: 6.76  / point x 50  -> max: 33.80  %
        251-300: 5.92  / point x 50  -> max: 29.58  % 
        301+:    5.07  / point x 
"""
class DamageSimulator:
    def __init__(self, config):
        # Adding this variable
        self.const_offset = config['app_settings']['desired_ap_to_constitution']
        self.base_stats = config['base_stats']
        self.level, self.primary, self.primary_base, self.secondary, self.secondary_base = config['character'].values()
        self.attributes, self.primary_data, self.secondary_data = self.pop_attrs(self.primary, self.secondary, config['weapons'])
        self.simulations = self.pop_possibilities(self.const_offset)

    # https://newworld.fandom.com/wiki/Attributes
    def calculate_available_ap(self, level):
        if 0 < level <= 13:
            result = level * 2 - 2
            return result
        
        elif 14 <= level <= 40:
            return self.calculate_available_ap(13) + (level - 13) * 3
        
        elif 41 <= level <= 55:
            return self.calculate_available_ap(40) + (level - 40) * 4

        elif 56 <= level <= 60:
            return self.calculate_available_ap(55) + (level - 55) * 5

    def calculate_level_scaling(self, level):
        return (level-1)*.025

    # start at 5, ignore first 5 of any stat
    def calculate_ap_scaling(self, stat):
        if 5 <= stat <= 100:
            return (stat - 5) * 0.01625
        
        elif 101 <= stat <= 150:
            return self.calculate_ap_scaling(100) + ((stat - 100) * 0.013)

        elif 151 <= stat <= 200:
            return self.calculate_ap_scaling(150) + ((stat - 150) * 0.0117)
        
        elif 201 <= stat <= 250:
            return self.calculate_ap_scaling(200) + ((stat - 200) * 0.0104)

        elif 251 <= stat <= 300:
            return self.calculate_ap_scaling(250) + ((stat - 250) * 0.0091)

        elif 301 <= stat:
            return self.calculate_ap_scaling(300) + ((stat - 300) * 0.0078)

        else:
            return 0.0

    def calculate_damage_one_attr(self, b_dmg, lvl, attr, base_attr_level):
        levelscaling = self.calculate_level_scaling(lvl)
        apscaling = self.calculate_ap_scaling(attr)
        base = b_dmg
        return b_dmg * ( self.calculate_level_scaling(lvl) + self.calculate_ap_scaling(attr + base_attr_level) + 1 )

    def calculate_damage_two_attr(self, b_dmg, lvl, attr_primary, attr_secondary, base_attr_level_primary, base_attr_level_secondary):
        return b_dmg * ( 1 + self.calculate_level_scaling(lvl) + self.calculate_ap_scaling(attr_primary + base_attr_level_primary) * 0.9 + self.calculate_ap_scaling(attr_secondary + base_attr_level_secondary) * 0.65 )

    def pop_attrs(self, primary, secondary, weapon_data):
        ret = []
        primary_data = weapon_data[primary]
        secondary_data = weapon_data[secondary]
        
        if primary_data['multi']:
            ret += [primary_data['attr1'], primary_data['attr2']]

        else:
            ret.append(primary_data['attr1'])

        if secondary_data['multi']:
            if secondary_data['attr1'] not in ret:
                ret.append(secondary_data['attr1'])
            
            if secondary_data['attr2'] not in ret:
                ret.append(secondary_data['attr2'])

        else:
            if secondary_data['attr1'] not in ret:
                ret.append(secondary_data['attr1'])

        return (ret, primary_data, secondary_data)        

    def generate_simulation(self, possible_ap_configurations):
        for configuration in possible_ap_configurations:
            ret = []
            ret += configuration
            if self.primary_data['multi']:
                primary_main_attr = configuration[self.attributes.index(self.primary_data['attr1'])]
                primary_sub_attr = configuration[self.attributes.index(self.primary_data['attr2'])]
                ret.append(self.calculate_damage_two_attr(self.primary_base, self.level, primary_main_attr, primary_sub_attr, self.base_stats[self.primary_data['attr1']], self.base_stats[self.primary_data['attr2']]))

            else:
                primary_main_attr = configuration[self.attributes.index(self.primary_data['attr1'])]
                ret.append(self.calculate_damage_one_attr(self.primary_base, self.level, primary_main_attr, self.base_stats[self.primary_data['attr1']]))

            if self.secondary_data['multi']:
                secondary_main_attr = configuration[self.attributes.index(self.secondary_data['attr1'])]
                secondary_sub_attr = configuration[self.attributes.index(self.secondary_data['attr2'])]
                ret.append(self.calculate_damage_two_attr(self.secondary_base, self.level, secondary_main_attr, secondary_sub_attr, self.base_stats[self.secondary_data['attr1']], self.base_stats[self.secondary_data['attr2']]))

            else:
                secondary_main_attr = configuration[self.attributes.index(self.secondary_data['attr1'])]
                ret.append(self.calculate_damage_one_attr(self.secondary_base, self.level, secondary_main_attr, self.base_stats[self.secondary_data['attr1']]))

            ret.append(sum([ret[-1], ret[-2]]))
            yield ret

    def pop_possibilities(self, const_offset):
        possibility_index = []
        usable_ap = self.calculate_available_ap(self.level) - const_offset
        
        for x in range(len(self.attributes)):
            possibility_index.append([x for x in range(0, usable_ap + 1, 1)])

        all_combinations = itertools.product(*possibility_index)
        #filtering out possibilities that don't use all of the available points
        all_combinations = [x for x in all_combinations if sum(x) == usable_ap]

        simulation_data = [x for x in self.generate_simulation(all_combinations)]

        simulation_data =  pd.DataFrame(simulation_data, columns = self.attributes + ["Primary Weapon Damage", "Secondary Weapon Damage", "Combined Damage"])
        simulation_data.sort_values(["Combined Damage"], ascending=False, inplace=True)
        print("Simulations complete, printing top results, export of data can be found in this directory as output.csv")
        print(simulation_data.head(4))

        return simulation_data

    def export_data(self):
        self.simulations.to_csv('output.csv', index=False, header=True)



def get_config():
    with open('config.json') as f:
        d = json.loads(f.read())

    return d

if __name__ == '__main__':
    d = DamageSimulator(get_config())
    d.export_data()