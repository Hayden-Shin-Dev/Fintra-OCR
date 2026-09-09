from fintraocr.normalize import normalize,country_inverted_names

def test_documented_historical_names_preserve_country_identity_only():
 for name,code in [('Turkey','TR'),('Republic of Turkey','TR'),('Swaziland','SZ'),('Kingdom of Swaziland','SZ')]:
  assert normalize(name,'country')==(code,[])
 for name in ['Turkev','Turkey Logistics','Swaziland Ltd','Soviet Union','Yugoslavia']:
  assert normalize(name,'country')[0] is None

def test_inverted_country_names_use_registry_without_fuzzy_repair():
 assert normalize('Palestine','country')==('PS',[])
 assert normalize('Micronesia','country')==('FM',[])
 for raw in ['Korea','Virgin Islands','Palestine Logistics','Talwan']:
  assert normalize(raw,'country')[0] is None

def test_generated_country_aliases_are_unique_registry_prefixes():
 import pycountry
 for alias,code in country_inverted_names().items():
  matches={c.alpha_2 for c in pycountry.countries if c.name.split(',',1)[0].strip().casefold()==alias}
  assert matches=={code}
