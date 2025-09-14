import streamlit as st
import requests

st.set_page_config("Recherche - Médiathèque","📚")

@st.cache_data(show_spinner=True)
def recherche_google_books(query, max_results=10):
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "maxResults": max_results
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Erreur API Google Books : {response.status_code}")

    data = response.json()
    livres = []

    for item in data.get("items", []):
        volume_info = item.get("volumeInfo", {})
        images = volume_info.get("imageLinks", {})
        extrait = volume_info.get("previewLink", None)
        selflink = item.get("selfLink")

        titre = volume_info.get("title", "Titre inconnu")
        auteurs = volume_info.get("authors", ["Auteur inconnu"])
        description = volume_info.get("description", "Pas de description disponible")

        # Choix de la meilleure image disponible
        couverture = (
            images.get("extraLarge") or
            images.get("large") or
            images.get("medium") or
            images.get("thumbnail") or
            "src/no_couverture.png"
        )
        # Recherche ISBN
        isbn = "ISBN non disponible"
        for ident in volume_info.get("industryIdentifiers", []):
            if ident.get("type") in ["ISBN_13", "ISBN_10"]:
                isbn = ident.get("identifier")
                break

        livres.append({
            "titre": titre,
            "auteurs": auteurs,
            "isbn": isbn,
            "couverture": couverture,
            "description": description,
            "lien_extrait": extrait,
            "selflink": selflink
        })

    return livres
if "run" not in st.session_state:
    st.session_state.run = 1
else:
    st.session_state.run = st.session_state.run+1

st.title("RECHERCHE MEDIATHEQUE")
if st.session_state.run == 1 and "search" in st.query_params:
    query = st.text_input("Votre recherche :",value=st.query_params.search)
else:
    query = st.text_input("Votre recherche :")

if query:
    st.query_params.search = query
    response = recherche_google_books(query)
    st.write("---")
    for book in response:
        col1, col2,col3 = st.columns([0.8,2,0.7],vertical_alignment="center")
        with col1:
            st.image(book["couverture"],width=128)
        with col2:
            st.write(book["titre"])
            st.write(str(", ".join(book["auteurs"])))
        with col3:
            url = f"/book_page?result={book['selflink']}&title={book["titre"]}"

            # Bouton HTML stylisé

            st.markdown(f"""
    <style>
    a {{
        text-decoration: none !important;
    }}
    .st-emotion-cache-zmhlmb {{
        background-color: #8BB0C4;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: 500;
        font-size: 16px;
        cursor: pointer;
        transition: background-color 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 3rem;
        text-decoration: none !important;
    }}
    .st-emotion-cache-zmhlmb:hover {{
        background-color: #3E81A3;
    }}
    .st-emotion-cache-olx2ca {{
        margin: 0;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        text-decoration: none !important;
    }}
    .st-emotion-cache-olx2ca p {{
        margin: 0;
        text-decoration: none !important;
    }}
    </style>

    <a href="{url}" style="text-decoration: none !important;">
        <button kind="secondary" data-testid="stBaseButton-secondary" aria-label=""
                class="st-emotion-cache-zmhlmb e1haskxa2">
            <div data-testid="stMarkdownContainer" class="st-emotion-cache-olx2ca e1hznt4w0">
                <p>Voir plus</p>
            </div>
        </button>
    </a>
""", unsafe_allow_html=True)

        st.write("---")