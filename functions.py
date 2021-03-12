import re
from difflib import SequenceMatcher
import roman
from fuzzywuzzy import fuzz
from os import system, name

# ************************************************* preprocessing *******************************************************

#Rozszerza imiona patronow w formacie "b. chrobry" do pelnego imienia i nazwiska, jesli rozwinieta para wystapila w danych inicjalizacyjnych
class NameExtender:
    """
    fields:
    :extenders -> Dict of dicts. First one is first letter of name second one surname. Value is tuple :(words count in replacement, full replacement str)
    """
    __shortcut_regex=re.compile(r"^(\w)\s*(\w*)")
    __white_regex=re.compile(r"\s+")
    
    def __init__(self,names):
        """
        Create names filler
        :names Preprocessed array of names, first for is name following ones are surname. Empty records and ones starting with name shortcut are valid and ignored
        """
        self.extenders={}
        
        valid_regex=re.compile(r"^\w\w+ \w+")
        
        #Get possible extenders
        extenders={}
        for name in names:
            name=name.strip()
            name=NameExtender.__white_regex.sub(' ',name)
            
            if name=='':
                continue
            if not valid_regex.match(name):
                continue
            
            name_letter=name[0]
            
            if str.isdigit(name_letter):
                continue
            
            white_index=name.find(' ')
            
            end_index=name.find(' ',white_index+1)
            if end_index==-1:
                end_index=len(name)
            surname=name[white_index+1:end_index]
            
            if len(surname)<3 or str.isnumeric(surname):
                continue
            
            key=(name_letter,surname)
            if key in extenders:
                if not name in extenders[key]:
                    extenders[key].append(name)
            else:
                extenders[key]=[name]
        
        #Filter extenders
        for key,value in extenders.items():
            num=len(value)
            
            if num==1:  #Sure extender
                extenders[key]=value[0]
                continue
            if num==2:  #Valid only if similarity >.85
                if SequenceMatcher(a=value[0],b=value[1]).ratio()>.85:
                    extenders[key]=value[0]
                else:
                    extenders[key]=None
                continue
            
            #Get average distance to each entry
            accuracy=[]
            for entry in value:
                partial=0
                for entry2 in value:
                    if not entry is entry2:
                        partial+=SequenceMatcher(a=entry,b=entry2).ratio()
                accuracy.append(partial/(len(value)-1))
            mx=max(accuracy)
            
            if mx<.9 or min(accuracy)<.77:  #filter out sets with big distance
                extenders[key]=None
                continue
            
            extenders[key]=value[accuracy.index(mx)]
        
        #Push all extenders into main extenders dict
        for key,value in extenders.items():
            if not value is None:
                value=(value.count(' ')+1,value)
                
                if key[0] in self.extenders:
                    self.extenders[key[0]][key[1]]=value
                else:
                    self.extenders[key[0]]={key[1]:value}
    
    def extend(self,st):
        """
        Extends single name. Works with pandas DataFrame.apply
        :st string to extends
        :return String from argument with extended name shortcuts
        """
        st=st.strip()
        st=NameExtender.__white_regex.sub(' ',st)
        
        ret=st
        search_index=0
        while True:
            match=NameExtender.__shortcut_regex.search(ret,search_index)
            
            if not match:
                break
            
            start=match.start(0)
            end=match.end(0)
            
            # Filter out matches inside words
            if not (start==0 and end==len(ret) or
                    start==0 and ret[end]==' ' or
                    ret[start-1]==' ' and end==len(ret) or
                    ret[start-1]==' ' and ret[end]==' '):
                search_index=end
                continue
            
            # print(ret,':',ret[start:end],':',ret[match.start(1):match.end(1)],':',ret[match.start(2):match.end(2)])
            
            first_letter=ret[match.start(1):match.end(1)]
            if first_letter in self.extenders:
                extender=self.extenders[first_letter]
                
                full_name=None
                
                surname=ret[match.start(2):match.end(2)]
                if surname in extender:  #Direct surname-template_surname match
                    full_name=extender[surname]
                else:  #Non direct, time for SequenceMatcher
                    accuracy=[(key,SequenceMatcher(a=key,b=surname).ratio()) for key in extender.keys()]
                    mx=max(accuracy,key=lambda x:x[1])
                    
                    if mx[1]<.9:
                        search_index=end
                        continue
                    
                    full_name=extender[mx[0]]
                
                if not full_name is None:
                    if full_name[0]==2:
                        ret=ret[:start]+full_name[1]+ret[end:]
                    else:
                        pass  #TODO implement name extending of multi words surnames
            search_index=start+1
        
        return ret

__roman_regex=re.compile("([lcdmxvi]+)")
#Zamien rzymskie liczby w stringu na arabskie odpowiedniki
def __roman_to_arabic(st):
    """Returns string with greek numbers replaced with arabic ones"""
    
    token_val={'i':1,'v':5,'x':10,'l':50,'c':100,'d':500,'m':1000}
    
    ret=st
    search_index=0
    prepost_chars=[' ',',','.']  #valid chars before or after roman occurrence
    while True:
        match=__roman_regex.search(ret,search_index)
        
        if not match:
            break
        
        start=match.start(0)
        end=match.end(0)
        
        # Filter out matches inside words
        if not (start==0 and end==len(ret) or
                start==0 and ret[end] in prepost_chars or
                ret[start-1] in prepost_chars and end==len(ret) or
                ret[start-1] in prepost_chars and ret[end] in prepost_chars):
            search_index=end
            continue
        
        roman=ret[match.start(1):match.end(1)]
        last_token_val=10e10
        value=0
        for i in range(len(roman)):
            current_token_val=token_val[roman[i]]
            if current_token_val>last_token_val:
                if last_token_val*10<current_token_val:  #misplaced symbols, most likely it's word containing only roman set letters
                    search_index=end
                    break
                value-=2*last_token_val
            
            value+=current_token_val
            
            last_token_val=current_token_val
        else:
            ret=ret[:start]+str(value)+ret[end:]
    return ret

#rozszesz popularne skroty typow szkul
def school_type_shortcut_extender(st):
    shortcuts={
        "lo":" liceum ogólnoształcące ",
        "l.o":" liceum ogólnoształcące ",
        "sms":" szkoła mistrzostwa sportowego ",
        "zso":" zespół szkół ogólnokształcących ",
        "zsz":" zespół szkół zawodowych ",
        "zesp.":" zespół ",
        "zs":" zespół szkół ",
        "z.sz":" zespół szkół ",
        "zs.":" zespół szkół ",
        "zse":" zespół szkół ",
        "zsm":" zespół szkół ",
        "zsp":" zespół szkół ",
        "nlo":" niepubliczne liceum ogólno kształcące ",
        "ckziu":"centrum kształcenia zawodowego 1 ustawicznego ",
        "zakł":" zakład ",
        "elekt":" elektryczny ",
        "elektr":" elektryczny ",
        "mechan":" mechanizczny ",
        "dzdz":" dolnoślaski zakład doskonalenia zawodowego ",
        "ktk":" katolickie towarzystw kultur ",  #not full words for better fuzzy match
        "pzps":" polski związek piłki siatkowej "
    }
    
    suffix=['','.']
    
    ret=st
    for key in shortcuts.keys():
        for suf in suffix:
            index=ret.find(key+suf)
            
            if index==-1:
                continue
            
            key_len=len(key)
            
            if not (index==0 or str.isnumeric(ret[index-1]) or ret[index-1]==' '):  #Begin not valid
                continue
            
            if not (index+key_len==len(ret) or str.isnumeric(ret[index+key_len]) or ret[
                index+key_len]==' '):  #End not valid
                continue
            
            ret=ret[:index]+shortcuts[key]+ret[index+3:]
    
    return ret

# okrelenie stopnia podobienstwa dwoch stringow
def w_similar(a, b):
    if a != None and b != None:
        return SequenceMatcher(None, a, b).ratio()
    else:
        return 0


# normalizowanie charow, polskie znaki -> ASCII
def normalize_char(c):
    if type(c) == str:
        c = c.lower()
        pol = ['ą', 'ć', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż']
        ASCII = ['a', 'c', 'e', 'l', 'n', 'o', 's', 'z', 'z']
        for i in range(len(pol)):
            if c == pol[i]:
                c = ASCII[i]
        return c


def normalize_string(s):
    if type(s) == str:
        rs = ''
        # usuwanie polsich znakow
        for i in s:
            rs += normalize_char(i)
        # usuwanie zbednych spacji
        rs = ' '.join(rs.split())
        return rs


# wektor z nazwami do usuniecia
str_base = ['os.', 'ul.', 'al.', 'pl.' 'os', 'ul', 'al', 'pl', 'ulica', 'plac', 'aleja', 'osiedle']


# usuwanie zbednych nazw -> ul, al, os itp.
def delstr(s):
    for b in str_base:
        if s == b:
            s = ''
            return s
    return s


# usuniecie 'ul.', 'pl.', 'ul', 'pl' itp. z nazw ulic
def del_ul(s):
    re = ""
    if type(s) == str:
        s = s.split()
        for e in s:
            re += delstr(e) + ' '
    return re


# szablon do znajdowania kodu pocztowego
def post_code(s):
    post_code = re.compile(r'\d\d-\d\d\d')
    pc_patt = post_code.search(s)
    if pc_patt != None:
        return pc_patt.group()
    else:
        return None


# szblon do znajdowania numeru budynku
def num_find(s):
    n = re.findall(r'\d+\w', s)
    if n != []:
        return n
    else:
        n = re.findall(r'\d+', s)
    return n


# przetworzenie wektora numeru budynku, normalizowanie numerow zlozonych z dwoch cyfr
def num_stan(s):
    if len(s) == 1:
        return s[0]
    # 20 i 4 -> 20/4
    elif len(s) > 1:
        return s[0] + '/' + s[1]


# szblon do znajdowania numeru w nazwie ulicy np. 1-ego maja
# -1 -> -go, -2 -> -ego, brak - 0
def num_street_find(s):
    s = s.replace(' ', '')

    n = re.match(r'(.*)-go', s)
    if n != None:
        return n.group(1), str(-1)

    n = re.match(r'(.*)-ego', s)
    if n != None:
        return n.group(1), str(-2)

    else:
        return '', str(0)


# czyszczenie stringow ze zbednych znakow
def ad_clean(s):
    getVals = list([val for val in s if val.isalpha() or val.isnumeric() or val == ' '])
    result = "".join(getVals)
    return result


# ujednolicenie liczb w nazwach szkół na rzymskie
def isNotBlank(myString):
    return bool(myString and myString.strip())


def school_name(s):
    if isNotBlank(s) == True:
        s = normalize_string(s)
        n = s.split()
        r = []
        for j in range(len(n) + 1):
            r.append(False)
        for i in range(len(n)):
            r[i] = n[i].isnumeric()
            if r[i] == True:
                n[i] = int(n[i])
                if n[i] < 5000:
                    n[i] = roman.toRoman(n[i])
                    n[i] = n[i].lower()
                n[i] = str(n[i])
            napis = ' '.join(n)
        return napis
    else:
        return s

# usuniecie 'w' i 'we' z nazw szkol
def w_out(s):
    n = s.split()
    for i in range(len(n)):
        if n[i] == "w" or n[i] == 'we':
            return ' '.join(n[:i])
    return ' '.join(n)


# usuniecie patrona z nawy szkoly
def patron_out(s):
    n = s.split()
    for i in range(len(n)):
        if n[i] == "im." or n[i] == "im" or n[i] == "imienia":
            return ' '.join(n[:i])
    return ' '.join(n)


# dodanie patrona do nazwy szkoly
def patron_in(s):
    s = s.replace('.', ' ')
    n = s.split()
    flaga = 0
    for i in range(len(n)):
        if n[i] == "im." or n[i] == "im" or n[i] == "imienia":
            flaga = 1
            return ' '.join(n[i + 1:])
    if flaga == 1:
        return ' '.join(n)
    else:
        return ''

# usuniecie skrotu  nr, nr. i numer
def nr_out(s):
    s = s.replace('nr ', ' ')
    s = s.replace('nr. ', ' ')
    s = s.replace('numer ', ' ')
    return s


# usuniecie '-'
def dash_out(s):
    s = s.replace('-', ' ').split(' ', 1)[0]
    return s


# szblon do znajdowania typu szkoly
def school_type_find(s):
    s = s.replace(' ', '')

    t = s.find('liceum')
    if t != -1:
        return 'liceum ogolnoksztalcace'

    t = s.find('lo')
    if t != -1:
        return 'liceum ogolnoksztalcace'

    t = s.find('technikum')
    if t != -1:
        return 'technikum'

    t = s.find('zespolszkol')
    if t != -1:
        return 'zespol szkol i placowek oswiatowych'

    return None


# pobieranie okreslonych wartosci skladowych adresu
def find_adress(s_ci, s_ad, school):
    # adresy
    adress = s_ad
    # miasto
    city = s_ci

    # usuniecie ulicy, miasta
    adress = del_ul(normalize_string(adress))
    city = normalize_string(city)
    school_type = school_type_find(normalize_string(school))
    adress = adress.replace(city, '')

    # znajdowanie kodu pocztowego, usuniecie go
    postcode = post_code(adress)
    adress = adress.replace(str(postcode), '')

    # sprawdzenie, czy w nazwie ulicy nie ma liczby (np. 1-ego maja)
    num_street_name, flag = num_street_find(adress)

    if int(flag) == 0:
        pass

    # -go
    if int(flag) == -1:
        adress = adress.replace(num_street_name, '')
        adress = adress.replace('-go', '')

    # -ego
    if int(flag) == -2:
        adress = adress.replace(num_street_name, '')
        adress = adress.replace('-ego', '')

    # znajdowanie numeru budynku
    num_w = num_find(adress)
    for n in num_w:
        adress = adress.replace(n, '')

    # przetworzenie wektora num
    if num_w != None:
        num = num_stan(num_w)

    adress = ad_clean(adress)

    return city, school_type, num_street_name + ' ' + adress, num, postcode


# utworzenie pustego wektora
def empty_vector(len):
    return [None for i in range(len)]

# sprawdzenie, czy string jest pusty
def is_string_empty(s):
    r = re.search('[a-zA-Z]', s)
    if r != None:
        return False
    else:
        return True


def dictionary_of_cities(of_exl):
    dict_of_names = {}
    for i in range(len(of_exl)):

        if str(of_exl.iloc[i, 3]) in dict_of_names:
            dict_of_names[str(of_exl.iloc[i, 3])].append(i)
        else:
            dict_of_names[str(of_exl.iloc[i, 3])] = [i]
    return dict_of_names

# ************************************************* dopasowanie *******************************************************


# czyszczenie terminala
def clear():
    if name == 'nt':
        _ = system('cls')
    else:
        _ = system('clear')


def find2(i, lista, norm_data_js_exl, of_exl):
    ac = 0
    dic_of_prop = {}

    id = norm_data_js_exl.iloc[i, 0]
    city = norm_data_js_exl.iloc[i, 1]
    school_name = norm_data_js_exl.iloc[i, 2]
    school_type = norm_data_js_exl.iloc[i, 3]
    street = norm_data_js_exl.iloc[i, 4]
    house_num = norm_data_js_exl.iloc[i, 5]
    pst_code = norm_data_js_exl.iloc[i, 6]

    for nr in lista:
        if is_string_empty(street) == False:
            fu = fuzz.partial_ratio(street, str(of_exl.iloc[nr, 4]))
            fu = fu / 100
        else:
            fu = 0

        if fu > 0.80:
            t = w_similar(school_type, of_exl.iloc[nr, 1])
            if t == None:
                t = 0

            d = w_similar(str(house_num), str(of_exl.iloc[nr, 5]))
            if d == None:
                d = 0

            if is_string_empty(school_name) == False:
                fs = fuzz.token_sort_ratio(school_name, of_exl.iloc[nr, 2])
                fs = fs / 100
            else:
                fs = 0

            ac = 1 * t + 4 * fu + 1 * d + 6 * fs

            ac = round((ac / 12.0) * 100, 2)

        if ac > 50 and fu > 0.80:
            dic_of_prop[of_exl.iloc[nr, 7]] = ac

    dic_of_prop_sorted = sorted(dic_of_prop.items(), key=lambda kv: kv[1], reverse=True)
    if len(dic_of_prop_sorted) == 0:
        return 'Prawdopodobnie błędne dane'
    else:
        return dic_of_prop_sorted[:5]


def find(min, max, norm_data_js_exl, of_exl, dict_of_names):
    # MIN  - dolny zakres
    # MAX  - gorny zakres danych z jsosa
    MIN = min
    MAX = max

    of_school_table = []
    of_school_org_table = []
    of_school_loc_table = []
    prop_table = []
    status = []
    rspo_table = []
    prop = {}
    test = {}
    for i in range(MIN, MAX):
        max_prop = 0
        ac_max_idx = 0
        ac = 0

        id = norm_data_js_exl.iloc[i, 0]
        city = norm_data_js_exl.iloc[i, 1]
        school_name = norm_data_js_exl.iloc[i, 2]
        school_type = norm_data_js_exl.iloc[i, 3]
        street = norm_data_js_exl.iloc[i, 4]
        house_num = norm_data_js_exl.iloc[i, 5]
        pst_code = norm_data_js_exl.iloc[i, 6]
        patron = norm_data_js_exl.iloc[i, 7]
        flaga = 0

        for key in dict_of_names.keys():
            if w_similar(norm_data_js_exl.iloc[i, 1], str(key)) == 1:
                miasto = str(key)
                flaga = 1
                break

        if flaga == 1:
            lista = dict_of_names[miasto]

            for nr in lista:

                m = w_similar(city, of_exl.iloc[nr, 3])
                if m == None:
                    m = 0

                t = w_similar(school_type, of_exl.iloc[nr, 1])
                if t == None:
                    t = 0

                d = w_similar(str(house_num), str(of_exl.iloc[nr, 5]))
                if d == None:
                    d = 0

                if is_string_empty(school_name) == False:
                    fs = fuzz.token_sort_ratio(school_name, of_exl.iloc[nr, 2])
                    fs = fs / 100
                else:
                    fs = 0

                if is_string_empty(street) == False:
                    fu = fuzz.partial_ratio(street, str(of_exl.iloc[nr, 4]))
                    fu = fu / 100
                else:
                    fu = 0

                # miasta musza sie zgadzac
                if m > 0.93 and fu != 0:
                    ac = 1 * t + 4 * fu + 1 * d + 6 * fs
                    ac = round((ac / 12.0) * 100, 2)

                elif m > 0.93:
                    if is_string_empty(patron) == False:
                        fp = fuzz.partial_ratio(patron, str(of_exl.iloc[nr, 8]))
                        fp = fp / 100
                    else:
                        fp = 0
                    ac = 1 * t + 4 * fs + 8 * fp
                    ac = round((ac / 13.0) * 100, 2)

                if ac > max_prop:
                    max_prop = ac
                    ac_max_idx = nr

            if max_prop < 50:
                of_school_loc_table.append('Brak wystarczających danych')
                status.append('Brak wystarczających danych')
                of_school_org_table.append("-")
                prop_table.append(max_prop)

            elif is_string_empty(street) == True and max_prop < 80:
                of_school_loc_table.append('Brak wystarczających danych')
                status.append('Brak wystarczających danych')
                of_school_org_table.append("-")
                prop_table.append(max_prop)

            elif max_prop < 87:
                prop_table.append('50-87')
                of_school_loc_table.append(of_exl.iloc[ac_max_idx, 3])
                status.append('niepewny')
                lista_proponowanych = find2(i, lista, norm_data_js_exl, of_exl)
                of_school_org_table.append(lista_proponowanych)

            else:
                prop_table.append(str(max_prop))
                of_school_loc_table.append(of_exl.iloc[ac_max_idx, 3])
                status.append('pewny')
                of_school_org_table.append(of_exl.iloc[ac_max_idx, 7])

        elif flaga == 0:
            prop_table.append('Brak podanego miasta w bazie')
            of_school_loc_table.append('Brak podanego miasta w bazie')
            status.append('Brak podanego miasta w bazie')
            of_school_org_table.append('Brak podanego miasta w bazie')

        print(round( (i - MIN) / (MAX - MIN) * 100, 2), '%')

    return of_school_loc_table, prop_table, status, of_school_org_table

