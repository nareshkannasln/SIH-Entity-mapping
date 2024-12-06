from langchain_ollama import OllamaLLM  # Updated import for Ollama
import time

# Initialize Llama 3.1 model from Ollama
llm = OllamaLLM(model="gemma2:9b", temperature=0)

# Define the prompt template for JSON validation
template = """
You are a wonderful entity extraction and translation model. You are given a JSON input and a raw text. You need to extract the values from the raw text based on the keys provided in the JSON input. The keys in the JSON input are as follows:

Identify the corresponding value in the raw text and extract the value. The value is a string that follows the key in the raw text.
Try possible variations of the key to extract the value. For example, if the key is "name", try extracting the value using "name", "Name", "NAME", etc.
Transform the extracted value to the correct data type. For example, if the key is "total_mark", the value should be transformed to a number.
Output the result as an array with the extracted values in the order of the keys in the JSON input.
Try translating the raw text to English to check if the raw text is in a different language.
If value for the key is not found, output ''(this is the string with 0 length) for that index.

Translation Requirements:
If any of the field not found in english, then try tranlating the native language to english and extract the value.
If value obtained via this cases, the translated value should be returned.
Note: This is optional, if entity already obtained in english, no need to translate.

Input:
JSON Input: {}

Raw Text: {}

Document Type: 
- marksheet
- community_certificate
- transfer_certificate
- bonafide_certificate
- other

Strict Instructions:
- Output only the array result.
- Ensure the output adheres strictly to array formatting, with no additional characters outside the array structure.
- Include the type of the document in the 0th index of the array.
- Do not include any debugging information in the output.
- Maintain the order of values for each keys in the JSON for the array result.
- Your output should only start from '[' and end with ']'.

Exact output format:
{}

Output the trsnalated value for the key "name" in the raw text.
Array should only contain english translated value for the key.
Translations should be perfect and no errors should be there.
"""

# Input schema for JSON validation
json_input = {
    "name": "String, Avoid prefix or suffix denotations but initial should be included",
    "date_of_birth": "Date Format (DD-MM-YYYY) Date format should be in numbers",
    "degree": "String, Full name of the degree(10th/12th/Graduation)",
    "cgpa": "Float, this data may be worsely unformatted refer properly, range 0-10",
    "percentage": "Float, this data may be worsely unformatted refer properly, range 0-100",
    "class": "String, Class of the candidate(Such as First Class, Second Class or Distinction)"
}

raw_text = """
சான்றிதழ் வ.எண்/ சான்றிதழ் S. எண். SEC. 0200757 ரசுத் தேர்வுகள் துறை, சென்னை - 600 000 அரசுத் தேர்வுகள் துறை, சென்னை - டநிலைக் கல்வி பள்ளி இறுதி வகுப்புச் சான்றிதழ CONDARY SCHOOL LEAVING GERTIFICATI- பத்தாம் வரம்பு X STANDARDY அதிகாரத்திற்கு உட்பட்டது தமிழ்நாடு அரசு தேர்வுகள் OF THE GOVERNMENT OF TAMILNADU தேர்வர் ரமேஷ் P N MAR . 2003 இல் பத்தாம் வகுப்புப் பொதுத் தேர்வெழுதிக் கீழ்க்காணும் விழுக்காட்டு மதிப்பெண்களைப் பெற்றுள்ளார் என்று சான்றளிக்கப்படுகிறது. மேலே குறிப்பிட்டுள்ள விண்ணப்பதாரர் எஸ்எஸ்எல்சி பொதுத் தேர்வில் கலந்துகொண்டு பின்வரும் சதவீத மதிப்பெண்களைப் பெற்றுள்ளார் என்று சான்றளிக்கப்பட்டது SCIENCE மொத்தம் THREE SEVEN ZERO 370 - TOTAL பிறந்த நாள் / பிறந்த தேதி பதிவெண் / பதிவு எண். ம.அ.ப.குறியீட்டெண் & நாள் TMR CODE NO. & DATE 30.06.1988 24 2794 30.05.2003 A 21 36 69 பள்ளியின் பெயர் / SCHOOL GOVT B HSS BHAVANI பத்தாம் வகுப்புத் தேர்வில் தேர்ச்சி பெற ஒவ்வொரு பாடத்திலும், 100க்குக் குறும அளவு முப்பத்தை விழுக்காடு மதிப்பெண் பெற வேண்டும். இது பகுதி முறையில் தேர்வு எழுதித் தேர்ச்சி பெறுவதற்கும் பொருந்தும். SSLC (X STD.) தேர்வில் தேர்ச்சி பெறுவதற்கு, ஐந்து பாடங்களில் ஒவ்வொன்றிலும் குறைந்தபட்சம் முப்பத்தைந்து சதவீத மதிப்பெண்கள் தேவை. இது பிரிவு அமைப்பின் கீழ் கடந்து செல்வதையும் உள்ளடக்கியது. ள (கூடிமம், கமிப வேட்பாளர் கையொப்பம் ARD OF SCHOOL EXAMINATIONS, TAMIL NADL"""

# Format the prompt with the input data


# Execute the chain
while True:
    print("Execution started...")
    # raw_text = input("Enter text: ")
    start_time = time.time()
    array_schema = [f"Obtained {key} here" for key in json_input.keys()]
    formatted_prompt = template.format(json_input, raw_text, ["Obtained document_type here"]+array_schema)
    # print(formatted_prompt)
    # exit()
    result = llm.stream(formatted_prompt)


    ans = []
    current_value = ""
    inside_array = False


    raw_result = ""
    # Stream the result
    for chunk in result:
      print(chunk)
      raw_result += chunk
      if '[' in chunk:
        inside_array = True
        current_value = ""
      if ']' in chunk:
        inside_array = False
        if current_value:
          ans.append(current_value.strip().strip("\"'[]"))
          current_value = ""
      if inside_array:
        parts = chunk.split(',')
        for part in parts[:-1]:
          current_value += part
          ans.append(current_value.strip().strip("\"'[]"))
          current_value = ""
        current_value += parts[-1]
        if current_value.strip().endswith(']'):
          ans.append(current_value.strip().strip("\"'[]"))
          current_value = ""

    try:
      if len(ans)-1 != len(json_input):
        raise ValueError("Length mismatch between JSON input and extracted values")
      else:
        print("Document Type:", ans[0])
        for i, key in enumerate(json_input.keys()):
          print(f"{key}: {ans[i+1]}")
    except Exception as e:
      print(raw_result)
      print("\nError converting string to array:", e)

    print(f"Execution time: {time.time() - start_time:.2f} seconds")

    choice = input("Need to re-run(Yes/No) :")
    if choice.lower() == "no":
      break