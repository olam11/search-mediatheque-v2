import streamlit as st
import requests
import concurrent.futures
import urllib.parse
from bs4 import BeautifulSoup
import unicodedata
import json
import time


st.set_page_config(f"{st.query_params.title} - Recherche - Médiathèque","📖")

def enlever_accents(texte):
    texte_normalise = unicodedata.normalize('NFD', texte)
    texte_sans_accents = ''.join(c for c in texte_normalise if unicodedata.category(c) != 'Mn')
    return texte_sans_accents

@st.cache_data(show_spinner=False)
def giga_fonction(titre, auteur):

    def babelio(titre):
        time.sleep(0.5)
        url = "https://www.babelio.com/aj_recherche.php"

        headers = {
            "User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/142.0",
            "Origin": "https://www.babelio.com",
        }

        payload = {
            "isMobile": False,
            "term": f"{titre}"
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status() 
            raw_bytes = response.content
            decoded_text = raw_bytes.decode("utf-8")
            data = json.loads(decoded_text)
            if len(data) > 0:
                url = "https://www.babelio.com"+data[0]["url"]
                return {"result": url}
            return {"result": None}
        except requests.RequestException as req_err:
            print(f"Erreur de requête : {req_err}")
        except json.JSONDecodeError as json_err:
            print(f"Erreur de parsing JSON : {json_err}")
        return {"result": None}

    def roubaix(titre, auteur):
        try:
            # Encodage des paramètres pour l'URL
            titre_enc = urllib.parse.quote(titre)
            auteur_enc = urllib.parse.quote(auteur)
            result_titre = urllib.parse.quote(titre.replace("!", ""))
            result_auteur = f'"{urllib.parse.quote(auteur.replace("!", ""))}"'
            search_url = (
                f"http://www.mediathequederoubaix.fr/osiros/result/resultat.php?"
                f"type_rech=ra&bool%5B%5D=&index%5B%5D=titres_tous&value%5B%5D={titre_enc}"
                f"&bool%5B%5D=AND&index%5B%5D=auteurs_tous&value%5B%5D={auteur_enc}"
                f"&bool%5B%5D=AND&index%5B%5D=fulltext&value%5B%5D=&spec_expand=1"
            )
            
            result_url = (
                f"http://www.mediathequederoubaix.fr/osiros/result/notice.php?"
                f"queryosiros=titres_tous%3A%28{result_titre}%29%20AND%20auteurs_tous%3A%28{result_auteur}%29&spec_expand=1&sort_define=tri_titre&sort_order=1&osirosrows=10&osirosstart=0"
            )
            headers = {"User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/142.0"}
            response = requests.get(result_url, headers=headers, timeout=10)

            # Sauvegarde du contenu HTML dans roubaix.html
            with open("roubaix.html", "w", encoding="utf-8") as f:
                f.write(response.text)

            if response.status_code != 200 or "Aucune" in response.text:
                return {"search_page": search_url, "result": None}

            soup = BeautifulSoup(response.text, "html.parser")
            div_permalien = soup.find('div', id='contain_permalien')
            lien = div_permalien.get_text(strip=True) if div_permalien else None

            return {"search_page": search_url, "result": lien}

        except Exception as e:
            print(f"Erreur : {e}")
            return {"search_page": None, "result": None}
    
    def tourcoing(titre, auteur):
        try:
            titre_enc = urllib.parse.quote_plus(enlever_accents(titre))
            auteur_enc = urllib.parse.quote_plus(enlever_accents(auteur))
            search_url = f"https://mediatheques.tourcoing.fr/recherche-detaillee/detaillee/2/1/{titre_enc}/0/0/1/{auteur_enc}/perso"
            headers = {"User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/142.0"}
            response = requests.get(search_url, headers=headers)
            if response.status_code != 200:
                return {"search_page": search_url, "result": None}
            soup = BeautifulSoup(response.text, "html.parser")
            first_title_div = soup.find("div", class_="ntc-item__titre")
            if not first_title_div:
                return {"search_page": search_url, "result": None}
            h3_tag = first_title_div.find("h3")
            a_tag = h3_tag.find("a") if h3_tag else None
            if not a_tag or not a_tag.has_attr("href"):
                return {"search_page": search_url, "result": None}
            return {"search_page": search_url, "result": "https://mediatheques.tourcoing.fr/" + str(a_tag["href"])}
        except Exception:
            return {"search_page": None, "result": None}
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            "babelio": executor.submit(babelio, titre),
            "roubaix": executor.submit(roubaix, titre, auteur),
            "tourcoing": executor.submit(tourcoing, titre, auteur),
        }
        
        for key, future in futures.items():
            try:
                results[key] = future.result(timeout=4)
            except concurrent.futures.TimeoutError:
                print(f"Timeout sur la source : {key}")
                results[key] = {"search_page": None, "result": None}
            except Exception as e:
                print(f"Erreur sur la source {key} : {e}")
                results[key] = {"search_page": None, "result": None}
    return results
@st.cache_data(show_spinner=False)
def get_livre_depuis_lien(lien):
    response = requests.get(lien)
    if response.status_code != 200:
        raise Exception(f"Erreur API Google Books : {response.status_code}")

    item = response.json()
    id = item.get("id")
    volume_info = item.get("volumeInfo", {})
    images = volume_info.get("imageLinks", {})
    extrait = f"https://books.google.fr/books?id={id}&printsec=frontcover&hl=fr&source=gbs_ge_summary_r&cad=0#v=onepage&q&f=false"
    selflink = item.get("selfLink")

    titre = volume_info.get("title", "Titre inconnu")
    auteurs = volume_info.get("authors", ["Auteur inconnu"])
    description = volume_info.get("description", "Pas de description disponible")

    # Image en "large" uniquement
    couverture = f"https://books.google.com/books/content?id={id}&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api"
    isbn = "ISBN non disponible"
    for ident in volume_info.get("industryIdentifiers", []):
        if ident.get("type") in ["ISBN_13", "ISBN_10"]:
            isbn = ident.get("identifier")
            break

    # Informations supplémentaires utiles
    editeur = volume_info.get("publisher", "Éditeur inconnu")
    page_count = volume_info.get("pageCount", "Nombre de pages inconnu")
    langue = volume_info.get("language", "Langue inconnue")
    lien_achat = item.get("saleInfo", {}).get("buyLink")

    livre = {
        "titre": titre,
        "auteurs": auteurs,
        "isbn": isbn,
        "couverture": couverture,
        "description": description,
        "editeur": editeur,
        "pages": page_count,
        "langue": langue,
        "lien_extrait": extrait,
        "lien_achat": lien_achat,
        "selflink": selflink
    }

    return livre

try:
    with st.spinner(show_time=True):
        livre = get_livre_depuis_lien(st.query_params.result)
    col1,col2 = st.columns([3,9],vertical_alignment="center",)
    with col1:
        st.image(livre["couverture"])
    with col2:
        st.markdown(f"**Titre** : {livre['titre']}")
        st.markdown(f"**Auteur(s)** : {', '.join(livre['auteurs'])}")
        st.markdown(f"**Éditeur** : {livre['editeur']}")
        st.markdown(f"**ISBN** : {livre['isbn']}")
        st.markdown(f"**Pages** : {livre['pages']}")

    st.markdown("#### 📝 Description")
    st.markdown(livre["description"], unsafe_allow_html=True)
    with st.spinner(show_time=True):
        links = giga_fonction(livre["titre"],livre["auteurs"][0])
    st.markdown("#### 🔗 Liens utiles")
    if livre["lien_extrait"]:
        st.markdown(f"- 📄  [Lire un extrait]({livre['lien_extrait']})")
    if links["babelio"]["result"]:
        st.markdown(f"- ![📄](https://www.babelio.com/favicon.ico)  [Voir sur Babelio]({links["babelio"]["result"]})")
    if links["roubaix"]["result"]:
        st.markdown(f"- ![📄](http://www.mediathequederoubaix.fr/favicon.ico)  [Voir la page du livre à Roubaix]({links["roubaix"]["result"]})")
    if links["roubaix"]["search_page"]:
        st.markdown(f"- ![📄](http://www.mediathequederoubaix.fr/favicon.ico)  [Voir la page de recherche à Roubaix]({links["roubaix"]["search_page"]})")
    if links["tourcoing"]["result"]:
        st.markdown(f"- ![📄](https://mediatheques.tourcoing.fr/media/templates/site/c3rb/images/favicons/favicon-16x16.png)  [Voir la page du livre à Tourcoing]({links["tourcoing"]["result"]})")
    if links["tourcoing"]["search_page"]:
        st.markdown(f"- ![📄](https://mediatheques.tourcoing.fr/media/templates/site/c3rb/images/favicons/favicon-16x16.png)  [Voir la page de recherche à Tourcoing]({links["tourcoing"]["search_page"]})")
    # if links["lille"]["result"]:
    #     st.markdown(f"- [Voir la page du livre à Lille]({links["lille"]["result"]})")
    # if links["lille"]["search_page"]:
    #     st.markdown(f"- [Voir la page de recherche à Lille]({links["lille"]["search_page"]})")
    

except Exception as e:
    st.error(f"Une erreur est survenue : {e}")
