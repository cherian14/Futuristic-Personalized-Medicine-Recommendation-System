import pandas as pd
import numpy as np
import streamlit as st
import ast
import time
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# Silence warnings for clean display
import warnings
warnings.filterwarnings('ignore')

# Custom CSS for cinematic, dynamic, clean UI
st.markdown("""
<style>
/* Background & base */
body, .stApp {
    background: linear-gradient(135deg, #0a1a2a 0%, #001223 100%);
    color: #e0e6f1;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    transition: background 0.5s ease;
}

/* Header styles */
h1, h2, h3 {
    font-weight: 800;
    font-family: 'Segoe UI Black', sans-serif;
    color: #00ffa3;
    letter-spacing: 0.05em;
    text-shadow: 0 0 10px #00ffa3;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #001f3f;
    padding: 20px 15px;
    color: #8ab4f8;
    font-weight: 600;
}
[data-testid="stSidebar"] h1, h2, h3 {
    color: #00ffa3;
}

/* Buttons */
.stButton>button {
    background-color: #00ffa3;
    color: #001f3f;
    font-weight: 700;
    border-radius: 12px;
    border: none;
    padding: 12px 28px;
    font-size: 18px;
    transition: background-color 0.3s ease, color 0.3s ease;
    box-shadow: 0px 4px 12px rgba(0, 255, 163, 0.6);
}
.stButton>button:hover {
    background-color: #008755;
    color: #e0e6f1;
    cursor: pointer;
}

/* Tabs */
[role="tab"] {
    background: #003366;
    color: #a3d9ff;
    border-radius: 15px 15px 0 0;
    font-weight: 700;
    padding: 8px 20px;
    margin-right: 3px;
    transition: background-color 0.3s ease;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
[role="tab"][aria-selected="true"] {
    background: linear-gradient(45deg, #00ffa3, #008755);
    color: #001f3f;
    box-shadow: 0px 4px 15px rgba(0, 255, 163, 0.7);
}

/* Text areas */
textarea, input, select {
    background-color: #002c5f !important;
    color: #c0d6ff !important;
    border: 2px solid #00ffa3 !important;
    border-radius: 8px !important;
    font-size: 16px !important;
    padding: 8px !important;
    transition: border-color 0.3s ease;
}
textarea:focus, input:focus, select:focus {
    border-color: #00ffcb !important;
    outline: none !important;
}

/* Metrics boxes */
.metric-container {
    background: #003366;
    border-radius: 12px;
    padding: 18px 24px;
    box-shadow: 0 0 12px #00ffa3aa;
    text-align: center;
    font-weight: 600;
    color: #a3d9ff;
    margin-bottom: 20px;
}

/* Scrollbar for long lists */
::-webkit-scrollbar {
    width: 8px;
}
::-webkit-scrollbar-thumb {
    background: #00ffa3;
    border-radius: 20px;
}

/* Balloon animation (streamlit default) visually enhanced */
.st-balloons {
    filter: drop-shadow(0 0 8px #00ffa3);
}

/* Responsive columns and spacing */
@media (max-width: 768px) {
    .stButton>button {
        width: 100%;
        font-size: 16px;
    }
}
</style>
""", unsafe_allow_html=True)

# -- Load and preprocess data with caching --
@st.cache_data
def load_data():
    symptoms_df = pd.read_csv('symtoms_df.csv')
    symptoms_df = symptoms_df.iloc[:, 1:]  # Drop unnamed index if present
    symptoms_df.fillna('', inplace=True)

    all_symptoms = set()
    for col in ['Symptom_1', 'Symptom_2', 'Symptom_3', 'Symptom_4']:
        all_symptoms.update(symptoms_df[col].unique())
    all_symptoms = [s.strip() for s in all_symptoms if s.strip()]
    unique_symptoms = sorted(all_symptoms)

    data = []
    for _, row in symptoms_df.iterrows():
        symptom_set = set([row['Symptom_1'], row['Symptom_2'], row['Symptom_3'], row['Symptom_4']])
        symptom_set = {s.strip() for s in symptom_set if s.strip()}
        encoded = [1 if sym in symptom_set else 0 for sym in unique_symptoms]
        data.append(encoded + [row['Disease']])

    columns = unique_symptoms + ['Disease']
    encoded_df = pd.DataFrame(data, columns=columns)

    descriptions = pd.read_csv('description.csv').set_index('Disease')
    precautions = pd.read_csv('precautions_df.csv').iloc[:, 1:].set_index('Disease')
    workouts = pd.read_csv('workout_df.csv').iloc[:, 1:].set_index('disease')
    medications = pd.read_csv('medications.csv')
    medications['Medication'] = medications['Medication'].apply(ast.literal_eval)
    medications = medications.set_index('Disease')

    medicines = pd.read_csv('medicine.csv')
    medicines = medicines.drop_duplicates(subset=['Drug_Name', 'Reason'])
    return encoded_df, unique_symptoms, descriptions, precautions, workouts, medications, medicines

# -- Training model --
@st.cache_resource
def train_model(encoded_df):
    X = encoded_df.drop('Disease', axis=1)
    y = encoded_df['Disease']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    return model, X.columns, acc

# -- Prediction logic --
def predict_disease(model, features, user_symptoms):
    input_data = np.zeros(len(features))
    for sym in user_symptoms:
        if sym in features:
            idx = np.where(features == sym)[0][0]
            input_data[idx] = 1
    input_df = pd.DataFrame([input_data], columns=features)
    return model.predict(input_df)[0]

# -- Get medicine recommendations --
def get_recommendations(disease, descriptions, precautions, workouts, medications, medicines):
    desc = descriptions.loc[disease, 'Description'] if disease in descriptions.index else "No description available."
    prec_list = precautions.loc[disease].dropna().tolist() if disease in precautions.index else ["Consult a doctor."]
    workout_list = workouts.loc[disease.lower()].dropna().tolist() if disease.lower() in workouts.index else ["Stay active."]
    med_list = medications.loc[disease, 'Medication'] if disease in medications.index else ["No medications listed."]
    specific_meds = medicines[medicines['Reason'].str.lower() == disease.lower()]['Drug_Name'].unique().tolist()
    if specific_meds:
        med_list.extend(specific_meds)
    return desc, prec_list, workout_list, med_list

# -- Main app --
def main():
    st.title("🩺 Doctor Paradise - Futuristic Personalized Medicine Advisor")
    st.markdown("""
    ### Empower Your Health Journey with AI-Powered Precision  
    Experience a **sleek, cinematic** interface, designed to make your health decisions **intuitive, immersive, and effective**.  
    Select symptoms, get instant, personalized medical insights — all wrapped in a futuristic, story-driven UI! 🚀
    """)
    st.image("https://images.unsplash.com/photo-1510751007277-369fa0c1f4e4?auto=format&fit=crop&w=800&q=80", use_column_width=True)

    # Load data + train model once
    encoded_df, unique_symptoms, descriptions, precautions, workouts, medications, medicines = load_data()
    model, features, acc = train_model(encoded_df)

    # Sidebar input with searchable multiselect and dynamic count display
    st.sidebar.header("🔍 Select Your Symptoms")
    st.sidebar.write("Start typing to search and select multiple symptoms:")
    user_symptoms = st.sidebar.multiselect("Symptoms", unique_symptoms, help="Type to search symptoms...")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Model Accuracy", f"{acc:.2%}")
    with col2:
        st.metric("Available Symptoms", len(unique_symptoms))

    if st.sidebar.button("🔮 Predict & Recommend", key="predict_btn"):
        if not user_symptoms:
            st.sidebar.warning("Please select at least one symptom to proceed.")
            return

        with st.spinner("Analyzing your symptoms... Please wait 🧠"):
            time.sleep(1)  # UX pause simulation
            disease = predict_disease(model, features, user_symptoms)
        st.balloons()
        st.success(f"### Predicted Condition: {disease} ⚕️")

        desc, prec_list, workout_list, med_list = get_recommendations(
            disease, descriptions, precautions, workouts, medications, medicines
        )

        # Tabbed display with cinematic/clean styling
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Description", "⚠️ Precautions", "🏃 Workouts/Diet", "💊 Medications"
        ])
        with tab1:
            st.write(desc)
        with tab2:
            for item in prec_list:
                st.markdown(f"• {item}")
        with tab3:
            for item in workout_list:
                st.markdown(f"• {item}")
        with tab4:
            for item in med_list:
                st.markdown(f"• {item}")

        # Interactive symptom chart
        st.subheader("Your Selected Symptoms Overview")
        symptom_data = pd.DataFrame({'Symptoms': user_symptoms, 'Count': [1] * len(user_symptoms)})
        st.bar_chart(symptom_data.set_index('Symptoms'))

        st.info("""
        ⚠️ **Disclaimer:** This is AI-generated advice designed to assist.  
        Always consult a qualified healthcare professional before making medical decisions.
        """)

if __name__ == "__main__":
    main()
