from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="gemma2:9b", temperature=0.1)

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

Exact output format:
{}

Output the trsnalated value for the 'String' based data in the raw text.
Array should only contain english translated value for the key.
Translations should be perfect and no errors should be there.

Strict Instructions:
- Output only the array result.
- Ensure the output adheres strictly to array formatting, don't include any additional text in the response.
- Include the type of the document in the 0th index of the array.
- Do not include any debugging information in the output.
- Maintain the order of values for each keys in the JSON for the array result.
- Your output should only start from '[' and end with ']'.
"""

async def extract_entity(json_input, raw_text):
    # Format the prompt with the input data
    array_schema = [f"Obtained {key} here" for key in json_input.keys()]
    formatted_prompt = template.format(json_input, raw_text, ["Obtained document_type here"] + array_schema)

    print("Started streaming...")
    result = llm.stream(formatted_prompt)

    ans = ""

    # Stream the result and yield each chunk to the caller
    for chunk in result:
        ans += chunk
        print(ans)
    
    return ans