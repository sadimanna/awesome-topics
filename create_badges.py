venues = {
    "Conferences": [
        "NeurIPS","ICML","ICLR","NDSS","CVPR","ICCV","ECCV","COLT","UAI",
        "IJCAI","AAAI","AISTATS","KDD","WSDM","CCS","ACL","NAACL-HLT",
        "EMNLP","COLING","SIGIR","ICDE","ICDM","WACV","SIGCOMM","INFOCOM",
        "MobiCom","NSDI","WWW","OSDI","SOSP","ISCA","MLSys","DAC",
        "IEEE S&P","USENIX Security","ACM Multimedia","ALT","SIGMOD",
        "EuroSys","ICSE","STOC","CIKM","USENIX ATC"
    ],
    "Journals": [
        "Artificial Intelligence","Machine Learning","JMLR","IEEE TPAMI",
        "IEEE TIP","IEEE TSP","IEEE TNNLS","IEEE TAI","IEEE TKDE",
        "IEEE TBD","IEEE TCYB","IEEE TMI","IEEE TSMC","IEEE TETCI",
        "IEEE TETC","IEEE TITS","IEEE TIFS","IEEE TISSEC","IEEE TIST",
        "IEEE TITB","IEEE TKDD","IJCV","CVIU","PVLDB","IEEE TPDS",
        "ACM TOCS","ACM TODS","ACM TOS","IEEE TCAD","IEEE TC","FOCS",
        "Nature Machine Intelligence","Foundations and Trends in ML",
        "Pattern Recognition","Pattern Recognition Letters",
        "Medical Image Analysis",
        "Computerized Medical Imaging and Graphics",
        "Data Mining and Knowledge Discovery","Knowledge-Based Systems",
        "Information Sciences","Expert Systems with Applications",
        "IEEE Data Science","IEEE TASLP","TACL","Neural Networks",
        "Neurocomputing","Neural Computing and Applications","JAIR"
    ]
}

def badge(name, kind, color):
    label = name.replace(" ", "%20")
    return f"![{name}](https://img.shields.io/badge/{label}-{kind}-{color}?style=flat-square)"

for section, names in venues.items():
    print(f"\n## {section}\n")
    for n in names:
        print(badge(n, section[:-1], "blue" if section=="Conferences" else "green"))
