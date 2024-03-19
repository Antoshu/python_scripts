"Version 2.8"

import requests
import csv
import os
import unicodedata
import getpass as gt
from pathlib import Path

# define months, used to name the folders
months_list = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

# define all languages for data validation
available_laguages = ["hi", "fr", "ja", "it", "pt", "en", "es", "de", "hi", "ar", "nl"]

# languages which require no normalisation for the image names
no_norm = ["hi","it","en","ar","nl","jp"]


# the normaliser function takes in a word + language and returns a tuple containing the option name for amplify and S3
# The purpose of this function is to avoid lengthening the code in the case of multiple normalisation case, and clarifying where normalisation takes place
def normaliser_function(op, lan):
    # if language picked is in no_norm array, don't normalise, else apply normalisation
    if lan in no_norm:
        norm_option_amplify = op
        norm_option_s3 = norm_option_amplify

    # for a set of languages, we normalise the image name for Amplify ingestion but not for s3
    elif lan in ["fr","es","pt","de","it"]:
        norm_option_amplify = unicodedata.normalize("NFKD", op)
        norm_option_amplify = "".join(
            [c for c in norm_option_amplify if not unicodedata.combining(c)]
        )
        # copy normalisation for the second as there is no difference
        norm_option_s3 = op

    #as a default, don't normalise
    else:
        norm_option_amplify = op
        norm_option_s3 = norm_option_amplify
    return (norm_option_amplify, norm_option_s3)


# gets the user alias to create a path
# https://www.geeksforgeeks.org/how-to-get-the-current-username-in-python/
user = gt.getuser()
user_loc = Path(os.path.expanduser("~"))

# get the script location
script_location = Path(os.path.dirname(__file__))
# kettle data folder location
kettle_data_folder = Path("/Users/" + user + "/ETLEnv/DATA")
# the file created by the ETL has to be in the poll_automation folder. If it isn't check the ETL_TEMP_DIR variable in Kettle
data_file_location = Path(kettle_data_folder / "poll_automation")

# check what kind of quip we are looking at. Format varies based on CX and because of workflow differences, the folders have to be organised differently
if os.path.isfile(data_file_location / "image_data_for_script.csv"):
    quip_type = "OTD"
    file_name = "image_data_for_script.csv"
if os.path.isfile(data_file_location / "_HC_INGESTION_DATA.csv"):
    quip_type = "HC"
    file_name = "_HC_INGESTION_DATA.csv"

# check if the person wants to start from later on in the quip. Might be necessary if there are errors on some line, or if its a really long document
yes_no = 0
start_row = 1  # because there is a title
while yes_no != "n" and yes_no != "y":
    print(
        "Do you want to download images from the start? y/n (images will be overridden if they have the same name)"
    )
    yes_no = input()

if yes_no == "n":
    while start_row == 1:
        print("What row do you want to start from?")
        input_row = input()
        try:
            start_row = int(input_row)
            break
        except:
            print("Please type an integer.")
            continue

# ask for the user language. This is used to define what kind of normalisation (or not) to use
user_lang = ""
while user_lang not in available_laguages:
    print("What language do you need the script for? (ie: hi, fr, jp, it...)")
    input_lang = input()
    if input_lang in available_laguages:
        user_lang = input_lang
        break
    else:
        print("Please type a valid language among: " + ", ".join(available_laguages))
        continue

# running this for hc
if quip_type == "HC":
    # initalise increment
    i = 0
    # open in utf-8 because default creates an error with python on Windows
    with open(data_file_location / file_name, encoding="utf8") as csvfile:
        # set custom delimiter here
        data = csv.reader(csvfile, delimiter=",", quotechar='"')
        for row in data:
            i += 1
            # skip title row
            if row[0] == "title":
                continue

            if i < start_row:
                continue
            # find year and month to create folders for storing the images
            date = row[10]
            split_date = date.split("-")
            year = split_date[0]
            month = split_date[1]
            month_folder_name = months_list[int(month) - 1]

            # replace the slashes in category to avoid sillyness with paths
            category = row[1].replace("/", " - ")
            category = category.replace("\\", " - ")

            # get option images and ids
            option_ids = [row[7], row[8]]
            option_images = [row[5], row[6]]

            # create the directory for the particular category of the row. If the directory does not exist, create it
            directory = os.path.join(
                script_location, "HC - " + year, month_folder_name, category
            )
            all_img_dir = os.path.join(
                script_location, "HC - " + year, month_folder_name, "all_img_for_S3"
            )
            if not os.path.exists(directory):
                print("Making directory: " + directory)
                os.makedirs(directory)
            if not os.path.exists(all_img_dir):
                print("Making directory: " + all_img_dir)
                os.makedirs(all_img_dir)

            inc = 0
            for option in option_ids:

                # use normaliser function defined at code start
                (normalized_option_amplify, normalized_option_s3) = normaliser_function(
                    option, user_lang
                )

                # create the image names with the suffix
                new_image_name_amp = normalized_option_amplify + ".svg.x240.png"
                new_image_name_s3 = normalized_option_s3 + ".svg.x240.png"

                new_image_path = Path(directory + "/" + new_image_name_amp)
                all_image_path = Path(all_img_dir + "/" + new_image_name_s3)

                # print for logging and info
                print("category: " + category)
                print(new_image_path)

                # try to get the images and write them to files. If fail, custom error message + normal error message
                try:
                    response = requests.get(option_images[inc])
                    with open(new_image_path, "wb") as image_file:
                        image_file.write(response.content)

                    with open(all_image_path, "wb") as image_file:
                        image_file.write(response.content)

                except Exception as e:
                    print(
                        "Could not get image "
                        + normalized_option_amplify
                        + ". Please check the link is valid"
                    )
                    print("Error message: " + e)

                inc += 1


# running this for otd
if quip_type == "OTD":
    i = 0
    with open(Path(data_file_location / file_name), encoding="utf8") as csvfile:
        data = csv.reader(csvfile, delimiter=",", quotechar='"')
        for row in data:
            i += 1
            if row[0] == "year":
                continue
            # print(row)
            if i < start_row:
                continue

            year = row[0]
            month = row[1]

            # option ids columns
            option_ids = [row[2], row[4], row[6], row[8]]

            # option images columns
            option_images = [row[3], row[5], row[7], row[9]]

            # make up the folder name. It contains the day number and row number in the excel
            folder_name = "day number - " + str(i - 1) + ", line - " + str(i)

            directory = os.path.join(
                script_location, "OTD - " + year, month, folder_name
            )
            # we have a special directory where all the images get copied to as well. This facilitates S3 ingestions
            all_img_dir = os.path.join(
                script_location, "OTD - " + year, month, "all_img_for_S3"
            )

            if not os.path.exists(directory):
                print("Making directory: " + directory)
                os.makedirs(directory)
            if not os.path.exists(all_img_dir):
                print("Making directory: " + all_img_dir)
                os.makedirs(all_img_dir)

            inc = 0
            for option in option_ids:
                if option == "":
                    break

                # use normaliser function defined at code start
                (normalized_option_amplify, normalized_option_s3) = normaliser_function(
                    option, user_lang
                )

                # create the image names with the suffix
                new_image_name_amp = normalized_option_amplify + ".svg.x240.png"
                new_image_name_s3 = normalized_option_s3 + ".svg.x240.png"

                new_image_path = Path(directory + "/" + new_image_name_amp)
                all_image_path = Path(all_img_dir + "/" + new_image_name_s3)

                # gets the image from the web
                try:
                    response = requests.get(option_images[inc])
                    print("Got image " + new_image_name_amp)

                    # opens an image document and writes the retrieved image to it
                    with open(new_image_path, "wb") as image_file:
                        image_file.write(response.content)
                    print("Stored image in " + str(new_image_path))

                    with open(all_image_path, "wb") as image_file:
                        image_file.write(response.content)

                except Exception as e:
                    print(
                        "Could not get image "
                        + new_image_name_amp
                        + ". Please check the link is valid"
                    )
                    print("Error message: " + e)
                inc += 1
