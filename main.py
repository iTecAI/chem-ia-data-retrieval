from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import json, time, requests, re, math, csv

DRIVER = webdriver.Chrome()
DRIVER.get('https://ptable.com')

def manual_click(driver, selector):
    driver.execute_script(f'document.querySelector(\'{selector}\').click()')

def parse_element(el):
    soup = BeautifulSoup(el.get_attribute('innerHTML'),'html.parser')
    at_num = int(soup.select('b')[0].text)
    abbrev = soup.select('abbr')[0].text
    full_name = soup.select('em')[0].text
    weight = round(float(soup.select('data')[0].text.strip('()')))

    return {
        'atomic_number':at_num,
        'abbreviation':abbrev,
        'element_name':full_name,
        'weight':weight
    }

def parse_wiki(el):
    print(el.get_attribute('innerHTML'))

content = [parse_element(i) for i in DRIVER.find_elements_by_css_selector('li.Solid, li.Gas, li.Liquid, li.UnknownState')]

DRIVER.close()

for element in content:
    print('Processing element '+element["element_name"])
    page = requests.get(f'https://en.wikipedia.org/wiki/Isotopes_of_{element["element_name"].lower()}').text
    soup = BeautifulSoup(page, 'html.parser')
    isotopes = []
    table = soup.select_one('.mw-parser-output > table.wikitable tbody')
    table_rows = table.select('tr')[2:]
    print(f'Found {str(len(table_rows))} rows.')
    c = 0
    while c < len(table_rows):
        row = table_rows[c]
        if 'rowspan' in row.select('td')[0].attrs.keys():
            inc = int(row.select('td')[0].attrs['rowspan'])
        else:
            inc = 1
        try:
            neutron_item = BeautifulSoup(row.select('td')[2].decode_contents(),'html.parser')
            [i.decompose() for i in neutron_item.select('sup.reference, a')]
            hl_item = BeautifulSoup(row.select('td')[4].decode_contents(), 'html.parser')
            [i.decompose() for i in hl_item.select('sup.reference, a')]
            hl_item = hl_item.decode_contents().replace('<sup>','^').replace('</sup>','').replace('\n','').replace('<b>','').replace('</b>','').replace('\xa0','').replace('<span style="margin-left:0.25em;margin-right:0.15em;">×','*')
            if '<span class="nowrap">' in hl_item:
                hl_item = hl_item.split('</span>')[1]
            hl_item = re.sub(r'\(.\)','',re.sub(r'\(.{1,}\)','', ''.join([i for i in hl_item if ord(i)<128]))).replace('#','').replace('?','').replace(' ','').replace('~','').replace('[','').replace(']','')
            hl_item = hl_item.split('&')[0]

            if hl_item.startswith('<') or hl_item == '' or '<' in hl_item or not any(x in hl_item for x in ['s','ms','ns','m','min','y','h']) or '[' in hl_item:
                c += inc
                continue

            if 'stable' in hl_item.lower():
                hl_item = 'stable'
            else:
                hl_unit = ''
                hl_time = ''
                for x in hl_item:
                    if x in '0123456789.^*':
                        hl_time += x
                    else:
                        hl_unit += x
                if '^' in hl_time:
                    hl_time_temp = hl_time.split('^')
                    if hl_time_temp[0].endswith('10') and len(hl_time_temp) > 2:
                        hl_time_temp[0] = hl_time_temp[0][:len(hl_time_temp[0])-2]
                    print(hl_time_temp)
                    hl_time = eval(hl_time_temp[0])*(10**eval(hl_time_temp[1]))
                else:
                    hl_time = float(hl_time)
                hl_unit = hl_unit.replace('+','').replace('-','').replace(',','').replace('years','y').lower()
                conversion_factors = {
                    'ps':1e-12,
                    'ns':1e-9,
                    'μs':1e-6,
                    'ms':1e-3,
                    's':1,
                    'min':60,
                    'h':3600,
                    'd':86400,
                    'y':31536000
                }
                if hl_unit in conversion_factors.keys():
                    hl_item = hl_time*conversion_factors[hl_unit]
                else:
                    hl_item = hl_time+0

            neutron_item = re.sub(r'\(.\)','',re.sub(r'\(.{1,}\)','', neutron_item.decode_contents().replace('<sup>','^').replace('</sup>','').replace('\n',''))).replace('?','')
            neutron_item = ''.join([i for i in neutron_item if ord(i)<128]).replace(' ','')
            if any([not i in '0123456789' for i in neutron_item]):
                c += inc
                continue

            if neutron_item.startswith('<') or neutron_item == '':
                c += inc
                continue
            

            isotopes.append({
                "neutrons": int(neutron_item),
                "half_life": hl_item
            })
            print(isotopes[len(isotopes)-1])
        except IndexError:
            print('Stable isotope')
        except SyntaxError:
            pass
        c += inc
        
    element["isotopes"] = isotopes
    print(f'Found {str(len(isotopes))} isotopes. Waiting to reduce net load.')
with open('test.json','w') as f:
    f.write(json.dumps(content,indent=4))

final = []
for element in content:
    for isotope in element['isotopes']:
        data_point = {}
        data_point['Atomic #'] = element['atomic_number']
        data_point['Element'] = element['element_name'] + ' (' + element['abbreviation'] + ')'
        data_point['# Neutrons of Most Stable Isotope'] = element['weight'] - element['atomic_number']
        data_point['# Neutrons of This Isotope'] = isotope['neutrons']
        data_point['Difference in Neutrons'] = data_point['# Neutrons of This Isotope'] - data_point['# Neutrons of Most Stable Isotope']
        if isotope['half_life'] == 'stable':
            data_point['Half-Life (s)'] = 'stable'
            data_point['Half-Life - Distance from Mean (s)'] = 'stable'
            data_point['Half-Life - Proportion of Mean'] = 'stable'
            data_point['Half-Life - Orders of Magnitude Above/Below Mean'] = 'stable'
        else:
            data_point['Half-Life (s)'] = round(isotope['half_life'],3)
            data_point['Half-Life - Distance from Mean (s)'] = round(isotope['half_life'],3) - (sum([i['half_life'] for i in element['isotopes'] if i['half_life'] != 'stable']) / len(element['isotopes']))
            data_point['Half-Life - Proportion of Mean'] = round(isotope['half_life'],3)/(sum([i['half_life'] for i in element['isotopes'] if i['half_life'] != 'stable']) / len(element['isotopes']))
            try:
                data_point['Half-Life - Orders of Magnitude Above/Below Mean'] = round(math.log10(data_point['Half-Life - Proportion of Mean']),3)
            except ValueError:
                data_point['Half-Life - Orders of Magnitude Above/Below Mean'] = 0
        final.append(data_point)

with open('raw.csv','w') as f:
    fields = ['Atomic #','Element','# Neutrons of Most Stable Isotope','# Neutrons of This Isotope','Difference in Neutrons','Half-Life (s)','Half-Life - Distance from Mean (s)','Half-Life - Proportion of Mean','Half-Life - Orders of Magnitude Above/Below Mean']
    writer = csv.DictWriter(f,fieldnames=fields)
    
    writer.writeheader()
    writer.writerows(final)
