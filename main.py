# Tomasz Gniazdowski i Michał Łopatka
import pandas as pd
import functions as fun
from xlsxwriter.exceptions import FileCreateError

data_ofic = input('Proszę podać nazwę pliku zawierającego dane wzorcowe: ')
data_jsos = input('Proszę podać nazwę pliku zawierającego dane do normalizacji: ')

min = input('Proszę podać dolny zakres badanych danych (początkowy rekord brany pod uwagę w pliku ze szkołami kandydatów): ')
max = input('Proszę podać górny zakres badanych danych (ostatni rekord brany pod uwagę): ')
min, max = int(min), int(max)

# odczyt exceli danych wzorcowych i danych z jsosa
of_exl = pd.read_excel(data_ofic, index_col=None, header=0, usecols="A, N, D, E, P, Q, S, E")
of_exl["Nazwa oryginalna"] = of_exl["Nazwa"]
js_exl = pd.read_excel(data_jsos, index_col=None, header=0, usecols="A:D")


js_exl = js_exl.dropna(thresh=2)
js_kopia = js_exl.copy()
of_exl = of_exl.dropna(thresh=5)
of_kopia = of_exl.copy()
of_exl.head(5)


# obrobka danych wzorcowych
of_exl = of_exl.dropna(thresh=5)
of_exl['Numer RSPO'] = of_exl['Numer RSPO'].fillna(0.0).astype(float)
of_exl['Numer RSPO'] = of_exl['Numer RSPO'].astype(int)
of_exl['Typ'] = of_exl['Typ'].apply(fun.normalize_string)
of_exl['Miejscowość'] = of_exl['Miejscowość'].apply(fun.normalize_string)
of_exl['Nazwa'] = of_exl['Nazwa'].apply(fun.normalize_string)
of_exl['Ulica'] = of_exl['Ulica'].apply(fun.normalize_string)
of_exl['Ulica'] = of_exl['Ulica'].apply(fun.del_ul)
of_exl['Nazwa'] = of_exl['Nazwa'].apply(fun.w_out)
of_exl["Patron"] = of_exl["Nazwa"]
of_exl['Nazwa'] = of_exl['Nazwa'].apply(fun.patron_out)
of_exl['Patron'] = of_exl['Patron'].apply(fun.patron_in)
of_exl['Nazwa'] = of_exl['Nazwa'].apply(fun.nr_out)
of_exl['Nazwa'] = of_exl['Nazwa'].apply(fun.school_name)
print('Dane wzorcowe obrobione')

#obrobka danych z jsos
js_exl['SZKOLA_SR'] = js_exl['SZKOLA_SR'].apply(fun.normalize_string)
js_exl['LOKALIZACJA_SZKOLY_SR'] = js_exl['LOKALIZACJA_SZKOLY_SR'].apply(fun.normalize_string)
js_exl['ADRES_SR'] = js_exl['ADRES_SR'].apply(fun.normalize_string)
js_exl['ADRES_SR'] = js_exl['ADRES_SR'].apply(fun.del_ul)
js_exl['SZKOLA_SR'] = js_exl['SZKOLA_SR'].apply(fun.w_out)
js_exl["PATRON"] = js_exl['SZKOLA_SR']
js_exl['SZKOLA_SR'] = js_exl['SZKOLA_SR'].apply(fun.patron_out)
js_exl['PATRON'] = js_exl['PATRON'].apply(fun.patron_in)
js_exl['SZKOLA_SR'] = js_exl['SZKOLA_SR'].apply(fun.nr_out)
js_exl['SZKOLA_SR'] = js_exl['SZKOLA_SR'].apply(fun.school_name)
js_exl['SZKOLA_SR'] = js_exl['SZKOLA_SR'].apply(fun.school_type_shortcut_extender)
js_exl['LOKALIZACJA_SZKOLY_SR'] = js_exl['LOKALIZACJA_SZKOLY_SR'].apply(fun.dash_out)
print('Dane z jsos obrobione')

# normalizowanie, uzyskiwanie okreslonych danych
norm_data_adress = fun.empty_vector(len(js_exl.index))
norm_data_num = fun.empty_vector(len(js_exl.index))
norm_data_postcode = fun.empty_vector(len(js_exl.index))
norm_data_city = fun.empty_vector(len(js_exl.index))
norm_data_sch_typ = fun.empty_vector(len(js_exl.index))


for i in range(len(js_exl.index)):
    norm_data_city[i], norm_data_sch_typ[i], norm_data_adress[i], norm_data_num[i], norm_data_postcode[i] = fun.find_adress(
        str(js_exl.iloc[i, 2]), str(js_exl.iloc[i, 3]), str(js_exl.iloc[i, 1]))
print('Wyodrębnienie danych adresowych z jsos')


# utworzenie slownika z znormalizownymi danymi z jsos
norm_data = {'ID': js_exl['INE_OS_ID'], 'Miejscowość': norm_data_city, 'Nazwa szkoły': js_exl['SZKOLA_SR'],
             'Nazwa typu': norm_data_sch_typ, 'Ulica': norm_data_adress, 'Nr domu': norm_data_num,
             'Kod poczt.': norm_data_postcode}


# znormalizowane, poukladane dane z jsosa
norm_data_js_exl = pd.DataFrame(data=norm_data)
norm_data_js_exl['Miejscowość'] = norm_data_js_exl['Miejscowość'].apply(fun.dash_out)
norm_data_js_exl.loc[norm_data_js_exl['Miejscowość'] == 'nan'] = None
norm_data_js_exl.loc[norm_data_js_exl['Ulica'] == 'nan'] = None
norm_data_js_exl.loc[norm_data_js_exl['Nr domu'] == 'nan'] = None
norm_data_js_exl.loc[norm_data_js_exl['Kod poczt.'] == 'nan'] = None
norm_data_js_exl['ID'] = norm_data_js_exl['ID'].fillna(0.0).astype(float)
norm_data_js_exl['ID'] = norm_data_js_exl['ID'].astype(int)
norm_data_js_exl['PATRON'] = js_exl["PATRON"]

# utworznie slownika z miastami, wywolanie funkcji dopasowujacej
# of_exl = of_exl.drop(columns=['Patron'])
print('Rozpoczęcie dopasowywania ... ')
of_exl['Miejscowość'] = of_exl['Miejscowość'].apply(fun.dash_out)
of_exl = of_exl.reset_index(drop=True)
of_exl = of_exl.sort_values(by='Miejscowość')
dict_of_names = fun.dictionary_of_cities(of_exl)
of_exl = of_exl.sort_values(by='Miejscowość')
norm_data_loc_of_school, norm_data_prop, status_tab, norm_data_of_school_org = fun.find(min, max, norm_data_js_exl, of_exl, dict_of_names)
print('Dopasoswyanie zakończone')


print('Tworzenie pliku wynikowego ...')
# utworzenie excela zawierajacego dane wejsiowe z jsosa i dopasowania
final_data = {'ID kandydata': js_exl.iloc[min:max, 0], 'Miejscowość szkoły (wprowadzona)': js_exl.iloc[min:max, 2],
              'Miejscowość szkoły (znormalizowana)': norm_data_loc_of_school, 'Zgodność danych (%)': norm_data_prop,
              'Status': status_tab, 'Nazwa szkoły (niezmieniona)': js_kopia.iloc[min:max, 1],
              'Nazwa szkoły z bazy danych (niezmieniona)': norm_data_of_school_org}
norm_data_final = pd.DataFrame(data=final_data)

while True:
    try:
        norm_data_final.to_excel('plik_wynikowy.xlsx')
        break
    except FileCreateError as x:
        print("Nie mozna utworzyc pliku.")
        var=input("Sprobowac ponownie? y/n\nJesli plik jest otwarty w innym programie zamknij go.\n")
        if var=='y':
            continue
        break