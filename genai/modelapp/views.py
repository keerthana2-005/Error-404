import time
from venv import logger
from django.shortcuts import render,redirect
import os
import google.generativeai as genai
import requests
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Profile
from django.shortcuts import get_object_or_404
import markdown
import requests
import markdown
import logging
from django.shortcuts import render
import requests
import time
import markdown
from django.shortcuts import render
from django.contrib import messages
import logging





def signup(request):
    if request.method == "POST":
        email = request.POST.get('email')
        username = request.POST.get('username')
        password1 = request.POST.get('pass1')
        password2 = request.POST.get('pass2')
        age = request.POST.get('age')  # New age field

        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered!")
            return redirect('signup')
        if int(age)<0 or int(age)>100:
            messages.error(request,"Invalid Age!")
            return redirect('signup')

        # Create user and profile
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()

        # Save the age in the profile
        profile = Profile(user=user, age=int(age))  # Assuming age is an integer
        profile.save()
        

        messages.success(request, "Account created successfully!")
        return redirect('login')

    return render(request, 'modelapp/signup.html')


    
def welcome(request):
    return render(request, 'modelapp/welcome.html')
def contact(request):
    return render(request,'modelapp/contact.html')

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        
        
        if User.objects.filter(username=username).exists():
            user = authenticate(request, username=username, password=password)
            if user is not None:
                auth_login(request, user)
                return redirect('home')  
            else:
                messages.error(request, 'Invalid credentials, try again!')
        else:
            messages.error(request, 'User does not exist')

    return render(request, 'modelapp/login.html')


def logout(request):
    auth_logout(request)  # Logs out the user
    return redirect('login')

@login_required


def home(request):
    textInput = request.POST.get("textInput", "")
    nutrients = ""
    claims = ""
    nutritional_info = ""
    response_text_formatted = ""
    health_score = 0  # Initialize health score

    print(request.POST)
    try:
        profile = request.user.profile  # Assuming Profile model has a OneToOneField to User
        condition = profile.problemsInput  # Get problemsInput field from Profile model
    except Profile.DoesNotExist:
        condition = "Unknown"  
    print(condition)

    response_text = ""
    if request.method == 'POST':
        search_url = (
            f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={textInput}"
            "&search_simple=1&action=process&json=1&fields=product_name,brands,nutrition_grades,"
            "ingredients_text,nutriments,labels_tags"
        )

        # Retry logic for fetching product data
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.get(search_url)
                response.raise_for_status()  # Raise an error for bad status codes
                data = response.json()
                products = data.get('products', [])

                if products:
                    product = products[0]  # Get the first matching product
                    textInput = product.get('product_name', 'Unknown')
                    nutrients = product.get('nutriments', {})
                    claims = product.get('labels_tags', [])  # Fetching claims

                    nutritional_info = [
                        f"Energy: {nutrients.get('energy-kcal_100g', 'N/A')} kcal",
                        f"Fat: {nutrients.get('fat_100g', 'N/A')} g",
                        f"Saturated Fat: {nutrients.get('saturated-fat_100g', 'N/A')} g",
                        f"Carbohydrates: {nutrients.get('carbohydrates_100g', 'N/A')} g",
                        f"Sugars: {nutrients.get('sugars_100g', 'N/A')} g",
                        f"Fiber: {nutrients.get('fiber_100g', 'N/A')} g",
                        f"Proteins: {nutrients.get('proteins_100g', 'N/A')} g",
                        f"Salt: {nutrients.get('salt_100g', 'N/A')} g",
                        f"Sodium: {nutrients.get('sodium_100g', 'N/A')} g"
                    ]

                    # Calculate health score based on the nutritional information
                    health_score = calculate_health_score(nutrients)

                else:
                    print("Product not found.")
                break  # Exit the retry loop if successful
            except requests.RequestException as e:
                logger.error(f"Attempt {attempt + 1} - Error fetching product data: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print("Failed to retrieve product information after multiple attempts.")

        # Assuming your Geminai configuration and model are correct
        genai.configure(api_key="AIzaSyCfIa7R7gE9D-WhIdJl6rKrjqfkmXg3c_8")

        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 3000,
            "response_mime_type": "text/plain",
        }

        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=generation_config,
        )

        chat_session = model.start_chat(history=[])

        response = chat_session.send_message(
            f"Based on {nutrients}, {claims}, {nutritional_info}, generate a health analysis for the product {textInput} "
            f"for a particular person with {condition} as his medical condition. The format of the response should be structured with headings like this: "
            "1. Consumption Suitability: Assess whether the individual can safely consume this product. If not, specify the recommended daily intake. "
            "2. Claim Validation: Evaluate the product's claims and provide an objective analysis of their accuracy. "
            "3. Sustainable Development Impact: Analyze whether the product's ingredients contribute to sustainable development. "
            "4. Healthier Alternatives: Recommend alternative options that the user can consider in place of {textInput}. "
            "Give the outputs explicitly in English, other languages are prohibited."
        )

        response_text = response.text
        response_text_formatted = markdown.markdown(response_text)

    return render(request, 'modelapp/home.html', {
        'product_name': textInput,
        'nutritional_info': nutritional_info,
        'health_score': health_score,
        'response_text_formatted': response_text_formatted
    })
def calculate_health_score(nutrients):
    score = 100  # Start with a perfect score
    # Nutrient impact weights
    nutrient_weights = {
        'Energy': -0.2,        # Decrease score for higher energy (calories)
        'Fat': -1,                  # Decrease score for fat
        'Saturated Fat': -1,        # Decrease score for saturated fat
        'Carbohydrates': -1,        # Decrease score for carbs
        'Sugars': -1,               # Decrease score for sugars
        'Fiber': 0.5,               # Increase score for fiber
        'Proteins': 0.5,            # Increase score for proteins
        'Salt': -0.5                # Decrease score for salt
    }

    for nutrient, weight in nutrient_weights.items():
        value = nutrients.get(nutrient, 'N/A')  # Fetch nutrient value from API response
        
        # Debugging: Log the nutrient and its value
        print(f"Processing nutrient: {nutrient}, value: {value}")

        # Special handling for energy (kcal)
        if nutrient == 'energy-kcal' and isinstance(value, str):
            value = value.replace('kcal', '').strip()  # Remove kcal unit for energy

        # For other nutrients, remove 'g' (grams)
        if nutrient != 'energy-kcal' and isinstance(value, str):
            value = value.replace('g', '').strip()  # Remove 'g' for grams

        # Try converting to float
        try:
            value = float(value)  # Convert value to float
            score += value * weight
            print(f"Updated score with {nutrient}: {value * weight}, New score: {score}")
        except ValueError:
            print(f"ValueError: Could not convert nutrient '{nutrient}' value '{value}' to float.")

    # Rescale the score to be between 0 and 50
    final_score = max(0, min(50, (score / 2)))  # Dividing by 2 to cap score at 50
    print(f"Final health score: {final_score}%")
    return final_score
def logout(request):
    return render(request,"modelapp/login.html")

@login_required
def profile(request):
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == "POST":
        problemsInput = request.POST.get("problemsInput", "")
        diabetes = request.POST.get("diabetes", "")
        bp = request.POST.get("bp", "")
        profile_picture = request.FILES.get("profile_picture", None)

        # Save the form data to the profile
        profile.problemsInput = problemsInput
        profile.diabetes = diabetes
        profile.blood_pressure = bp
        # Assuming you want to save diabetes and bp to the profile model,
        # you should add those fields to your Profile model as well.
        # For example: profile.diabetes = diabetes
        # profile.blood_pressure = bp

        
        profile.profile_picture = profile_picture
        
        profile.save()

        return redirect('profile')

    return render(request, 'modelapp/profile.html', {'profile': profile})


    
    

def base(request):
    return render(request, 'modelapp/basenew.html')


# def index(request):
#   if request.method == 'POST':
#     product_name = request.POST.get("product_name","")
#     nutrients = ""
#     claims = ""
#     nutritional_info = ""
#     condition = User.objects.get(condition=condition)

#     # Fetch product information from OpenFoodFacts API
#     search_url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&action=process&json=1&fields=product_name,brands,nutrition_grades,ingredients_text,nutriments,labels_tags"
#     response = requests.get(search_url)
    

    # genai.configure(api_key="AIzaSyBPSa7Ss2Gr3DK_wDcmkMm861c_7A-u9jU")
#     # Create the model
#     generation_config = {
#         "temperature": 1,
#         "top_p": 0.95,
#         "top_k": 64,
#         "max_output_tokens": 10000,
#         "response_mime_type": "text/plain",
#     }

#     model = genai.GenerativeModel(
#         model_name="tunedModels/peopleai-sp9ruaca9v5z",
#         generation_config=generation_config,
#         # safety_settings = Adjust safety settings
#         # See https://ai.google.dev/gemini-api/docs/safety-settings
#     )

#     chat_session = model.start_chat(
#         history=[
#         ]
#     )

#     response = chat_session.send_message(f"Based on Product details name:{product_name},Nutrients:{nutrients},claims:{claims},nutritional_information:{nutritional_info}.Give a health analysis for a person having a {condition} the format of the result should be a heading \"health analysis\" and give some points on how the ingridients of the product can affect the person having {condition} also tell in how much quantity the user can consume the particular product in a day and the next heading should be \"recommended diet/food\" and some dietary guidance on what he or she can consume if they have {condition},Conclude by telling if the claims are true or false and elaborate shortly,AND MOST IMPORTANTLY , if any of the {product_name},{nutrients},{claims} or {nutritional_info} has values like N/A, take your own relavant values")


    




