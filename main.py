from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import json, time, requests, re

DRIVER = webdriver.Firefox()
DRIVER.get('https://ptable.com/#Isotopes')

def manual_click(driver, selector):
    driver.execute_script(f'document.querySelector(\'{selector}\').click()')

def parse_element(el):
    soup = BeautifulSoup(el.get_attribute('innerHTML'),'html.parser')
    at_num = int(el.get_attribute('data-atomic'))
    abbrev = soup.select('abbr')[0].text
    full_name = soup.select('em')[0].text

    return {
        'atomic_number':at_num,
        'abbreviation':abbrev,
        'element_name':full_name
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
            hl_item = hl_item.decode_contents().replace('<sup>','^').replace('</sup>','').replace('\n','').replace('<b>','').replace('</b>','').replace('\xa0','').replace('<span style="margin-left:0.25em;margin-right:0.15em;">×','')
            if '<span class="nowrap">' in hl_item:
                hl_item = hl_item.split('</span>')[1]
            hl_item = re.sub(r'\(.\)','',re.sub(r'\(....\)','', ''.join([i for i in hl_item if ord(i)<128]))).replace('#','')
            
            neutron_item = re.sub(r'\(.\)','',re.sub(r'\(....\)','', neutron_item.decode_contents().replace('<sup>','^').replace('</sup>','').replace('\n','')))
            neutron_item = ''.join([i for i in neutron_item if ord(i)<128])

            if neutron_item.startswith('<') or neutron_item == '':
                c += inc
                continue
            if hl_item.startswith('<') or hl_item == '' or '<' in hl_item or not any(x in hl_item for x in ['s','ms','ns','m','min','y','h']) or '[' in hl_item:
                c += inc
                continue
            

            isotopes.append({
                "neutrons": neutron_item,
                "half_life": hl_item
            })
            print(isotopes[len(isotopes)-1])
        except IndexError:
            print('Stable isotope')
        c += inc
        
    element["isotopes"] = isotopes
    print(f'Found {str(len(isotopes))} isotopes. Waiting to reduce net load.')
    time.sleep(1.5)
with open('test.json','w') as f:
    f.write(json.dumps(content,indent=4))
