import streamlit as st
import requests
from datetime import datetime
import base64

# Page Configuration
st.set_page_config(
    page_title="Textbook Generator Pro",
    page_icon="📘",
    layout="wide"
)

# Custom CSS to ensure visibility
st.markdown("""
<style>
    .download-btn {
        margin-top: 2rem;
        margin-bottom: 3rem;
    }
    .word-count-input {
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("📘 Textbook Generator Pro")
st.markdown("Generate professional textbooks for students")

# Main Form
with st.form("textbook_form", border=True):
    st.subheader("Textbook Specifications")
    
    # Layout columns
    col1, col2 = st.columns(2)
    
    with col1:
        subject = st.text_input("Subject Title*", 
                              placeholder="Enter the subject of your textbook",
                              help="The main subject of your textbook")
        
        grade = st.selectbox("Target Grade Level*", 
                           options=list(range(1, 13)),
                           index=7)  # Default to grade 8
    
    with col2:
        region = st.text_input("Region/Culture*", 
                             placeholder="Enter geographical/cultural context",
                             help="Geographical/cultural context")
        
        # Word count input with better visibility
        word_count = st.number_input(
            "Total Word Count*", 
            min_value=1000, 
            max_value=20000, 
            value=5000,
            step=500,
            key="word_count",
            help="Target length of your textbook",
            format="%d"
        )
    
    # Chapters and sections
    chapters = st.text_area(
        "Chapter Titles (comma separated)*",
        placeholder="Enter chapter titles separated by commas",
        height=100
    )
    
    sections = st.number_input(
        "Sections per Chapter*",
        min_value=2,
        max_value=10,
        value=5,
        step=1
    )
    
    # Detailed instructions
    prompt = st.text_area(
        "Content Instructions*",
        height=200,
        placeholder="Enter detailed instructions for content generation"
    )
    
    # Form submit with clear validation
    submitted = st.form_submit_button(
        "Generate Textbook",
        type="primary",
        use_container_width=True
    )

# Generation and Results Section
if submitted:
    if not all([subject, region, chapters, prompt]):
        st.error("Please fill all required fields (*)")
    else:
        chapters_list = [c.strip() for c in chapters.split(",")]
        
        data = {
            "subject": subject,
            "grade": grade,
            "region": region,
            "chapters": chapters_list,
            "sections_per_chapter": sections,
            "prompt": prompt,
            "word_count": word_count,
        }
        
        with st.spinner(f"Generating {word_count:,} word textbook..."):
            try:
                response = requests.post(
                    "http://localhost:8000/generate-textbook",
                    json=data,
                    timeout=300
                )
                
                if response.ok:
                    result = response.json()
                    actual_words = result["word_count"]
                    
                    # Success case
                    if actual_words >= 0.9 * word_count:
                        st.success(f"✅ Generated {actual_words:,} words")
                        
                        # Content preview
                        with st.expander("Preview Textbook Content"):
                            st.markdown(result["textbook_content"][:2000] + "...")
                        
                        # PDF download button
                        pdf_bytes = base64.b64decode(result["pdf"])
                        st.download_button(
                            label=f"📥 Download Full Textbook ({actual_words:,} words)",
                            data=pdf_bytes,
                            file_name=f"{subject.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            key="download_pdf",
                            type="primary",
                            use_container_width=True,
                            help="Click to download the complete textbook as PDF"
                        )
                    
                    # Partial success
                    else:
                        st.warning(f"⚠️ Generated {actual_words:,}/{word_count:,} words")
                        if st.button("Try Again with Larger Word Count"):
                            st.rerun()
                
                # Error cases
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
            
            except Exception as e:
                st.error(f"🚨 Generation failed: {str(e)}")

# Footer
st.divider()
st.caption("Textbook Generator Pro v2.0 | Word count guaranteed ")
