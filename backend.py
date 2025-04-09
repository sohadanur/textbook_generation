from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, conint, constr
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import os
from dotenv import load_dotenv
import logging
from fpdf import FPDF
import tempfile
import tiktoken
import base64

# Load environment variables
load_dotenv()

# Initialize Mistral client
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL")

if not MISTRAL_API_KEY or not MISTRAL_MODEL:
    raise ValueError("MISTRAL_API_KEY or MISTRAL_MODEL is not set. Check your .env file.")

mistral_client = MistralClient(api_key=MISTRAL_API_KEY)
tokenizer = tiktoken.get_encoding("cl100k_base")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class TextbookInput(BaseModel):
    subject: constr(min_length=1, max_length=50)
    grade: conint(ge=1, le=12)
    region: constr(min_length=1, max_length=50)
    chapters: list[constr(min_length=1, max_length=50)]
    sections_per_chapter: conint(ge=1, le=10)
    prompt: constr(min_length=10)
    word_count: conint(ge=500, le=20000)

def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text))

# In generate_pdf function (backend.py), replace with:
def generate_pdf(content: str, filename: str) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Clean content of problematic characters
    cleaned_content = content.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.multi_cell(0, 10, txt=cleaned_content)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    with open(temp_file.name, "rb") as f:
        pdf_bytes = f.read()
    os.unlink(temp_file.name)
    return base64.b64encode(pdf_bytes).decode('utf-8')

# def generate_pdf(content: str, filename: str) -> str:
#     pdf = FPDF()
#     pdf.add_page()
#     pdf.set_font("Arial", size=12)
#     pdf.multi_cell(0, 10, txt=content)
#     temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
#     pdf.output(temp_file.name)
#     with open(temp_file.name, "rb") as f:
#         pdf_bytes = f.read()
#     os.unlink(temp_file.name)
#     return base64.b64encode(pdf_bytes).decode('utf-8')

def generate_chunked_prompt(input: TextbookInput, current_content: str = "", current_count: int = 0) -> tuple[str, int]:
    remaining_words = input.word_count - current_count
    if remaining_words <= 0:
        return "", current_count

    chunk_prompt = f"""
    Continue generating content for this {input.subject} textbook.
    Current word count: {current_count}/{input.word_count}
    Remaining words needed: {remaining_words}
    
    STRUCTURE:
    Chapters: {", ".join(input.chapters)}
    Sections per chapter: {input.sections_per_chapter}
    
    CONTENT REQUIREMENTS:
    1. Generate exactly {min(2000, remaining_words)} words
    2. Focus on sections with least content
    3. Add detailed examples and analysis
    4. Maintain consistent style
    
    CURRENT CONTENT:
    {current_content[-5000:] if current_content else "No content yet"}
    """
    return chunk_prompt, remaining_words

@app.post("/generate-textbook")
async def generate_textbook(input: TextbookInput, request: Request):
    try:
        logger.info(f"Received request for {input.word_count} words")
        
        textbook_content = ""
        attempts = 0
        max_attempts = 5
        
        while len(textbook_content.split()) < input.word_count and attempts < max_attempts:
            attempts += 1
            prompt, remaining_words = generate_chunked_prompt(input, textbook_content, len(textbook_content.split()))
            
            messages = [
                ChatMessage(role="system", content=f"You are writing a {input.word_count}-word textbook. Current progress: {len(textbook_content.split())} words."),
                ChatMessage(role="user", content=prompt)
            ]
            
            response = mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                max_tokens=4000
            )
            
            new_content = response.choices[0].message.content
            textbook_content += "\n" + new_content
            
            current_count = len(textbook_content.split())
            logger.info(f"Attempt {attempts}: Added {len(new_content.split())} words (Total: {current_count})")
            
            if current_count >= input.word_count:
                break

        # Final word count verification
        final_word_count = len(textbook_content.split())
        if final_word_count < 0.8 * input.word_count:
            raise HTTPException(status_code=400, detail=f"Failed to reach target word count. Requested: {input.word_count}, Actual: {final_word_count}")

        # Generate PDF
        pdf_content = generate_pdf(textbook_content, f"{input.subject.replace(' ', '_')}.pdf")

        return {
            "textbook_content": textbook_content,
            "word_count": final_word_count,
            "pdf": pdf_content
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




# from fastapi import FastAPI, HTTPException, Request
# from pydantic import BaseModel, conint, constr
# from mistralai.client import MistralClient
# from mistralai.models.chat_completion import ChatMessage
# import os
# from dotenv import load_dotenv
# import logging

# # Load environment variables
# load_dotenv()

# # Initialize Mistral client
# MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
# MISTRAL_MODEL = os.getenv("MISTRAL_MODEL")

# if not MISTRAL_API_KEY or not MISTRAL_MODEL:
#     raise ValueError("MISTRAL_API_KEY or MISTRAL_MODEL is not set. Check your .env file.")

# mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# app = FastAPI()

# # Define the input model for the POST request
# class TextbookInput(BaseModel):
#     subject: constr(min_length=1, max_length=50)
#     grade: conint(ge=1, le=12)
#     region: constr(min_length=1, max_length=50)
#     chapters: list[constr(min_length=1, max_length=50)]  # List of chapter names
#     sections_per_chapter: conint(ge=1, le=10)
#     prompt: constr(min_length=10, max_length=500)
#     pages: conint(ge=5, le=100)  # Updated page range

# # Define the prompt template for textbook generation
# def generate_textbook_prompt(input: TextbookInput) -> str:
#     return f"""
#     Generate a textbook for the following details:
#     - Subject: {input.subject}
#     - Grade: {input.grade}
#     - Region: {input.region}
#     - Chapters: {", ".join(input.chapters)}
#     - Sections per Chapter: {input.sections_per_chapter}
#     - Prompt: {input.prompt}
#     - Total PagesWords: {input.pages}

#     Ensure the content is structured as follows:
#     1. Each chapter should have a clear title and introduction.
#     2. Each section within a chapter should be long and informative. 
#     3. Use simple language suitable according to the grade level.
#     4. Your articles are informative, detailed, and well-organized.
#     5. 
#     """
# @app.post("/generate-textbook")
# async def generate_textbook(input: TextbookInput, request: Request):
#     try:
#         logger.info(f"Received request: {input.dict()}")

#         # Generate the textbook prompt
#         prompt = generate_textbook_prompt(input)

#         # Create chat messages for Mistral API
#         messages = [
#             ChatMessage(role="system", content="You are a helpful assistant that generates textbooks."),
#             ChatMessage(role="user", content=prompt)
#         ]

#         # Call Mistral API to generate textbook content
#         response = mistral_client.chat(model=MISTRAL_MODEL, messages=messages)

#         # Extract the generated content
#         textbook_content = response.choices[0].message.content

#         logger.info("Textbook generated successfully.")
#         return {"textbook_content": textbook_content}
#     except Exception as e:
#         logger.error(f"Error generating textbook: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Error generating textbook: {str(e)}")

# # Run the FastAPI server
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)  
