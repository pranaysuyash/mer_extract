import os
from openai import OpenAI
import PyPDF2
from pdf2image import convert_from_path
import base64
import csv
import uuid
from dotenv import load_dotenv

load_dotenv(dotenv_path='/Users/pranay/Projects/Data_Science/computer_vision/proj3/scripts/.env')


# Set your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()
def create_unique_folder(base_path, prefix):
    unique_id = str(uuid.uuid4())[:8]  # Use first 8 characters of UUID
    folder_name = f"{prefix}_{unique_id}"
    folder_path = os.path.join(base_path, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def check_pdf_content_type(file_path):
    pdf_reader = PyPDF2.PdfReader(file_path)
    pages_with_text = []
    pages_with_images = []

    for page_number, page in enumerate(pdf_reader.pages):
        text = page.extract_text()
        if text:
            pages_with_text.append(page_number + 1)
        else:
            pages_with_images.append(page_number + 1)

    return pages_with_text, pages_with_images

def extract_images_from_pdf(file_path, output_folder):
    images = convert_from_path(file_path, dpi=200)
    image_paths = []
    for i, image in enumerate(images):
        image_path = os.path.join(output_folder, f"page_{i+1}.jpeg")
        image.save(image_path, 'JPEG')
        image_paths.append(image_path)

    return image_paths

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def call_openai_for_extraction(content, is_image=False):
    system_prompt = """You are an AI assistant tasked with extracting and formatting text from images 
    Your goal is to preserve the original structure as much as possible while presenting the information in a clean, structured manner that can be easily readable.

Please follow these instructions carefully:

1. Analyze the provided content to extract all text and checkbox information from the image.

2. Maintain the original structure and formatting of the document as much as possible.

3. Clearly separate section titles, headings, and any key pieces of information.

4. For checkboxes and their labels:
   a. Pay close attention to the proximity of checkboxes to their labels. The checkbox is always before the label.
   b. Format the output such that the checkbox is presented first, followed by its label.
   c. After providing all the options, indicate the response in BOLD on a separate line. 
   d. Make sure to recheck if all checkbox have been identified and their responses noted.
   e. If there are any checkboxes or lists in the document, preserve their structure as much as possible.
   f. If there are any Yes/No or any Option based columns in the document, preserve their structure as much as possible.

5. If there are any tables or lists in the document, preserve their structure as much as possible.
   Format tables using semantic markup, e.g. use <HTML> tags.

6. If you encounter any ambiguities or uncertainties in the extraction process, note them in [brackets] after the relevant information.

7. Ensure the output is clean, structured, and formatted properly for easy conversion into a CSV.

Reminders:
- If you're unsure about any element in the document, provide your best interpretation and include a note about the uncertainty.
- Do not include any personal analysis or additional information not present in the original document.
- Double-check that checkmarks are identified correctly and mentioned against the appropriate questions.

Please provide your extracted and formatted text within <extracted_content> tags. Remember to focus on accuracy, proper formatting, and clear presentation of the information.
"""

    user_prompt = """Please extract and format the content from the image according to the instructions."""

    try:
        if is_image:
            base64_image = encode_image(content)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}
                ],
                temperature=0
            )
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{user_prompt}\n\n{content}"}
                ],
                temperature=0
            )

        extracted_text = response.choices[0].message.content + "\n"
        
        # Extract content between <extracted_content> tags
        start_tag = "<extracted_content>"
        end_tag = "</extracted_content>"
        start_index = extracted_text.find(start_tag)
        end_index = extracted_text.find(end_tag)
        
        if start_index != -1 and end_index != -1:
            extracted_text = extracted_text[start_index + len(start_tag):end_index].strip()
        
        return extracted_text

    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return ""

def process_pdf(file_path, output_folder):
    pages_with_text, pages_with_images = check_pdf_content_type(file_path)
    extracted_data = []

    # Process text pages
    pdf_reader = PyPDF2.PdfReader(file_path)
    for page_number in pages_with_text:
        text = pdf_reader.pages[page_number - 1].extract_text()
        extracted_text = call_openai_for_extraction(text)
        extracted_data.append({'page': page_number, 'extracted_text': extracted_text})

    # Process image pages
    image_paths = extract_images_from_pdf(file_path, output_folder)
    for image_path in image_paths:
        page_number = int(os.path.basename(image_path).split('_')[1].split('.')[0])
        if page_number in pages_with_images:
            extracted_text = call_openai_for_extraction(image_path, is_image=True)
            extracted_data.append({'page': page_number, 'extracted_text': extracted_text})

    return extracted_data

def save_to_csv(extracted_data, csv_filename):
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['Page', 'Extracted Text'])
        for data in extracted_data:
            writer.writerow([data['page'], data['extracted_text']])

def process_file(file_path):
    extracted_data = process_pdf(file_path, 'temp_images')
    
    # Create a unique folder for this file's outputs
    base_name = os.path.basename(file_path)
    output_folder = os.path.join('outputs', os.path.splitext(base_name)[0])
    os.makedirs(output_folder, exist_ok=True)
    
    # Sort the extracted data by page number
    extracted_data.sort(key=lambda x: int(x['page']))
    
    # Generate individual HTML files and combined HTML content
    combined_html = "<html><body>"
    for data in extracted_data:
        page_html = f"<h1>Page {data['page']}</h1>\n<pre>{data['extracted_text']}</pre>"
        
        # Save individual page HTML
        page_file = os.path.join(output_folder, f"page_{data['page']}.html")
        with open(page_file, 'w') as f:
            f.write(f"<html><body>{page_html}</body></html>")
        
        # Add to combined HTML
        combined_html += f"{page_html}\n<hr>\n"
    
    combined_html += "</body></html>"
    
    # Save combined HTML
    combined_html_file = os.path.join(output_folder, f"{base_name}_combined.html")
    with open(combined_html_file, 'w') as f:
        f.write(combined_html)
    
    # Save the CSV with proper formatting
    csv_filename = os.path.join(output_folder, f"{base_name}.csv")
    with open(csv_filename, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Page', 'Extracted Text'])
        for data in extracted_data:
            csv_writer.writerow([data['page'], data['extracted_text']])

    return combined_html_file, extracted_data

# Function to reprocess data with a schema (placeholder)
def reprocess_with_schema(filename, schema):
    # Add your schema processing logic here
    # Reprocess the extracted data based on schema
    return filename  # Return the reprocessed filename

# Function to process large files in chunks (placeholder)
def chunk_and_process(file_path):
    return process_file(file_path)