import streamlit as st
import os
import pandas as pd
import time
import io
import threading
from datetime import datetime
from dotenv import load_dotenv
from extractor import extract_multiple_api

st.set_page_config(page_title="💸 Finance Extractor", page_icon="💸", layout="wide")

# Load environment variables
load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")

# --- Password Gateway ---
def check_password():
    """Returns `True` if the user had the correct password."""
    if st.session_state.get("password_correct", False):
        return True

    def password_entered():
        # Read password from local .env or Streamlit Secrets
        expected_password = os.getenv("APP_PASSWORD")
        if not expected_password:
            try:
                expected_password = st.secrets["APP_PASSWORD"]
            except Exception:
                expected_password = "financeapp123" # Fallback

        if st.session_state["password"] == expected_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    st.title("🔒 Security Gateway")
    st.markdown("This application uses a private Gemini API key.")
    st.text_input("Enter the Access Password", type="password", on_change=password_entered, key="password")
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Incorrect password. Please try again.")
    return False

if not check_password():
    st.stop()
# ------------------------

# Sidebar Status
with st.sidebar:
    st.header("⚙️ Status")
    if api_key:
        st.success("✅ Gemini API Key found in .env")
    else:
        st.error("❌ Gemini API Key NOT found in .env")
        st.info("Please add `GEMINI_API_KEY=your_key_here` to your `.env` file.")

st.title("💸 Finance Record Extractor")
st.markdown("""
Upload screenshots of your bank transactions. The AI will find all entries and list them in a table.
You can then **copy the table** (using the hover button) and paste it directly into your Excel sheet!
""")

st.divider()

# File Uploader
uploaded_files = st.file_uploader(
    "Choose bank screenshots", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

if uploaded_files:
    # Reload environment variables on every interaction to catch .env updates
    load_dotenv(override=True)
    current_api_key = os.getenv("GEMINI_API_KEY")

    if not current_api_key:
        st.warning("⚠️ **API Key Missing!** Please paste your key into the `.env` file and save it, then click refresh.")
    else:
        if "extracted_data" not in st.session_state:
            st.session_state.extracted_data = None

        if st.button("🚀 Extract Transactions"):
            all_data = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            timer_text = st.empty()
            
            start_time = time.time()
            
            with st.spinner("AI is analyzing your images..."):
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Processing {file.name}...")
                    
                    # Update progress and elapsed time initially
                    elapsed = time.time() - start_time
                    timer_text.markdown(f"⏱️ **Elapsed Time:** {elapsed:.1f}s")
                    
                    # Temp save
                    temp_path = f"temp_{file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(file.getbuffer())
                    
                    # Variables to hold thread results
                    file_results = []
                    file_errors = []
                    
                    # Wrapper function for the thread
                    def threaded_extract(path, key, r_list, e_list):
                        try:
                            # Extract passing the latest key
                            res = extract_multiple_api(path, provided_key=key)
                            if res:
                                r_list.extend(res)
                        except Exception as e:
                            e_list.append(e)

                    # Start extraction in a background thread
                    extraction_thread = threading.Thread(
                        target=threaded_extract, 
                        args=(temp_path, current_api_key, file_results, file_errors)
                    )
                    extraction_thread.start()
                    
                    # Live timer loop while thread is running
                    while extraction_thread.is_alive():
                        elapsed = time.time() - start_time
                        timer_text.markdown(f"⏱️ **Elapsed Time:** {elapsed:.1f}s")
                        time.sleep(0.1)  # brief pause to prevent UI freezing
                        
                    # Cleanup thread
                    extraction_thread.join()
                    
                    # Process results
                    if file_errors:
                        st.error(f"An error occurred while processing {file.name}: {file_errors[0]}")
                    elif file_results:
                        all_data.extend(file_results)
                    else:
                        st.warning(f"No data found in {file.name}")
                        
                    # Cleanup temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
            
            total_duration = time.time() - start_time
            status_text.text("Done!")
            timer_text.markdown(f"🏁 **Total Extraction Duration:** {total_duration:.1f}s")
            
            if all_data:
                st.success(f"Found {len(all_data)} transactions across {len(uploaded_files)} images!")
                st.session_state.extracted_data = all_data
                st.balloons()
            else:
                st.error("Could not find any transactions in the uploaded images.")
                st.session_state.extracted_data = None

        if st.session_state.get("extracted_data"):
            # Convert to DataFrame
            df = pd.DataFrame(st.session_state.extracted_data)
            
            # 1. Rearrange columns: Wallet, Date, Merchant, Amount
            col_order = ["Wallet", "Date", "Merchant", "Amount"]
            existing_cols = [c for c in col_order if c in df.columns]
            df = df[existing_cols]
            
            # 2. Numbering starts from 1
            df.index = range(1, len(df) + 1)
            
            # 3. Format Data Types
            if "Amount" in df.columns:
                df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce')
            if "Date" in df.columns:
                # Convert string dates to datetime objects so st.data_editor can use DateColumn
                df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
            
            st.subheader("📊 Results Table")
            st.write("You can directly **edit** the table below. Select rows on the left and press **Delete** (or use the trash icon) to remove unneeded entries.")
            
            # Using st.data_editor to allow editing and deleting rows
            edited_df = st.data_editor(
                df, 
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "Amount": st.column_config.NumberColumn(
                        "Amount",
                        format="%,.0f", # Format as integer with locale-based thousand separator
                    ),
                    "Date": st.column_config.DateColumn("Date")
                }
            )
            
            st.write("*Tip: Hover over the table to see the Copy button on the top right.*")
            
            # Export to Excel feature
            st.subheader("💾 Export Data")
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                edited_df.to_excel(writer, index=False, sheet_name='Transactions')
                workbook  = writer.book
                worksheet = writer.sheets['Transactions']
                
                # Add thousands separator formatting in Excel output
                money_fmt = workbook.add_format({'num_format': '#,##0'}) 
                
                if "Amount" in edited_df.columns:
                    amt_idx = edited_df.columns.get_loc("Amount")
                    worksheet.set_column(amt_idx, amt_idx, 15, money_fmt)
                    
            current_time = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button(
                label="📥 Download as Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name=f"Transaction_{current_time}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
