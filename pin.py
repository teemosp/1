import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import LocateControl
import requests
import math
import re

st.set_page_config(layout="wide")

# ================= CSS FULL SCREEN =================
st.markdown("""
<style>
.block-container {
    padding: 0rem 1rem;
}

iframe {
    width: 100% !important;
    height: 95vh !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🗺️ VINFAST LIVE MAP")

# ================= GOOGLE SHEET =================
GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/1OfPyNThZAKcaNXo_O1x7lfQnmjBBbRWorpAkJAPUnoQ/export?format=csv&gid=1229149684"

# ================= LOAD DATA =================
@st.cache_data(ttl=30)
def load_data():

    gs_df = pd.read_csv(GOOGLE_SHEET_CSV)

    data = []

    for idx, row in gs_df.iterrows():

        try:
            ten = str(row.iloc[7]).strip()     # cột H
            toado = str(row.iloc[14]).strip()  # cột O

            if "," not in toado:
                continue

            coord = toado.replace(" ", "")
            coord = coord.replace("°", "")

            lat, lon = coord.split(",")

            lat = float(lat)
            lon = float(lon)

            data.append({
                "STT": len(data) + 1,
                "Ten diem": ten,
                "Toa do": f"{lat},{lon}",
                "Latitude": lat,
                "Longitude": lon
            })

        except:
            continue

    return pd.DataFrame(data)

df = load_data()

# ================= SAVE CSV =================
df[["STT", "Ten diem", "Toa do"]].to_csv(
    "toado.csv",
    index=False
)

# ================= DISTANCE =================
def haversine(lat1, lon1, lat2, lon2):

    R = 6371000

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(dlambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

# ================= DMS =================
def dms_to_decimal(degrees, minutes, seconds, direction):

    decimal = (
        float(degrees)
        + float(minutes) / 60
        + float(seconds) / 3600
    )

    if direction in ["S", "W"]:
        decimal *= -1

    return decimal

# ================= EXTRACT COORD =================
def extract_coord(text):

    text = text.strip()

    # ================= VN FORMAT =================
    # 20,49801° B, 105,75655° Đ

    vn_pattern = r'([0-9,]+)°?\s*[Bb],?\s*([0-9,]+)°?\s*[ĐD]'

    vn_match = re.search(vn_pattern, text)

    if vn_match:

        lat = vn_match.group(1).replace(",", ".")
        lon = vn_match.group(2).replace(",", ".")

        lat = float(lat)
        lon = float(lon)

        return lat, lon

    # ================= DMS FORMAT =================
    # 20°29'32.2"N 105°46'39.1"E

    dms_pattern = r'(\d+)°(\d+)\'(\d+\.?\d*)"?([NS])\s+(\d+)°(\d+)\'(\d+\.?\d*)"?([EW])'

    dms_match = re.search(dms_pattern, text)

    if dms_match:

        lat = dms_to_decimal(
            dms_match.group(1),
            dms_match.group(2),
            dms_match.group(3),
            dms_match.group(4)
        )

        lon = dms_to_decimal(
            dms_match.group(5),
            dms_match.group(6),
            dms_match.group(7),
            dms_match.group(8)
        )

        return lat, lon

    # ================= DECIMAL =================
    # 20.508400,105.770264

    match = re.search(
        r'(-?\d+\.\d+),\s*(-?\d+\.\d+)',
        text
    )

    if match:

        lat = float(match.group(1))
        lon = float(match.group(2))

        return lat, lon

    return None, None

# ================= MAP CENTER =================
center_lat = df["Latitude"].mean()
center_lon = df["Longitude"].mean()

# ================= MAP =================
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=13,
    tiles="https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
    attr="OpenStreetMap"
)

# ================= LOCATION BUTTON =================
LocateControl(auto_start=False).add_to(m)

# ================= FIT ALL POINTS =================
sw = [df["Latitude"].min(), df["Longitude"].min()]
ne = [df["Latitude"].max(), df["Longitude"].max()]

m.fit_bounds([sw, ne])

# ================= MARKERS =================
for i, row in df.iterrows():

    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],

        tooltip=f"{row['STT']}. {row['Ten diem']}",

        popup=f"""
        <b>{row['Ten diem']}</b><br>
        {row['Toa do']}
        """,

        icon=folium.DivIcon(html=f"""
            <div style="
                background-color: red;
                color: white;
                border-radius: 50%;
                width: 26px;
                height: 26px;
                text-align: center;
                font-size: 12px;
                line-height: 26px;
                font-weight: bold;
                border: 2px solid white;
            ">
                {row['STT']}
            </div>
        """)
    ).add_to(m)

# ================= SHOW MAP =================
st_folium(
    m,
    use_container_width=True,
    height=900
)

# ================= CHECK DISTANCE =================
st.subheader("📏 Check khoảng cách")

input_coord = st.text_input(
    "Nhập tọa độ hoặc link Google Maps"
)

if st.button("🔍 Check"):

    lat, lon = extract_coord(input_coord)

    if lat is None:

        st.error("❌ Không đọc được tọa độ")

    else:

        result = []

        for _, row in df.iterrows():

            dist = haversine(
                lat,
                lon,
                row["Latitude"],
                row["Longitude"]
            )

            result.append({
                "Tên điểm": row["Ten diem"],
                "Khoảng cách (m)": int(dist)
            })

        result_df = pd.DataFrame(result)

        result_df = result_df.sort_values(
            "Khoảng cách (m)"
        )

        st.success(
            f"📍 Gần nhất: "
            f"{result_df.iloc[0]['Tên điểm']} "
            f"({result_df.iloc[0]['Khoảng cách (m)']}m)"
        )

        st.dataframe(
            result_df.head(20),
            use_container_width=True
        )
