import re
import numpy as np
import pandas as pd


def get_field_info(field):
    strip_func = lambda x: re.sub("[^0-9a-z]", "", x.lower())
    if not "=" in field:
        return {}
    splitted = field.split("=")
    if len(splitted) == 2:
        field_name, value = splitted
        field_name = strip_func(field_name)
        if field_name == "author":
            value = value.split("and")
            new_authors = []
            for author in value:
                if "," in author:
                    author = author.split(", ")
                    new_authors.append(author[1] + " " + author[0])
                else:
                    new_authors.append(author)
            value = ", ".join(new_authors)
        value = strip_func(value)
        return {field_name: value}
    else:
        # try splitting up on commas
        fields_ = field.split(",")
        field_dict = {}
        for field_ in fields_:
            field_dict.update(get_field_info(field_))
        return field_dict   
        
def bib_to_df(bib_file, key_fields = None):
    if key_fields is None:
        key_fields = ["title", "author", "year", "journal"]
    with open(bib_file, "r") as f:
        content = f.read()
    list_of_references = content.split("@")[1:]
    df = pd.DataFrame(columns=["type", "key"])
    
    for reference in list_of_references:
        source_type = reference.split("{")[0].lower()
        key = reference.split("{")[1].split(",")[0].replace("\n", "")
        other_fields = reference.split(",\n")[1:]
        entry = {"type": source_type, "key": key, "original_bibtex": reference}
        for field in other_fields:
            res = get_field_info(field)
            entry.update(res)
        entry = pd.DataFrame([list(entry.values())], columns = list(entry.keys()))
        df = pd.concat([df, entry], ignore_index=True)
    
    return df


def match_old_new(old, new):
    new = new.rename(columns = {"key": "new_key"})
    old = old.rename(columns = {"key": "old_key"})

    matching_keys = ["year", "type", "author", "title"]

    matched = np.zeros((len(old), len(new)), dtype=int)
    convert_dict = {}
    for i, row in old.iterrows():
        print(i, row["old_key"])
        for j, new_row in new.iterrows():
            for field in matching_keys:
                if field in row and field in new_row:
                    if row[field] == new_row[field]:
                        matched[i, j] += 1

        # some asserts
        number_of_matches = (matched[i]>2).sum()
        if number_of_matches > 1:
            print("more than one match for", row["old_key"], ":", number_of_matches)
        elif number_of_matches == 0:
            print("no match for", row["old_key"])
            print(row[matching_keys])
            print(row["original_bibtex"])
        else:
            convert_dict[row["old_key"]] = new.iloc[np.argmax(matched[i])]["new_key"]

    assert ((matched>2).sum(1)==1).all()
    return convert_dict


def main(old_bibtex: str, new_bibtex: str, tex_file: str, new_tex_file: str):
    old_ = bib_to_df(old_bibtex)
    new_ = bib_to_df(new_bibtex)
    convert_dict = match_old_new(old_, new_)
    
    # read file
    with open(tex_file, "r") as f:
        tex_content = f.read()

    # replace all citations in the tex file with the new bibtex key
    # ensure all citations are in a \cite*{} command
    # use regex
    commands = [r"autocite", r"cite[^\{\}]"]
    for old_key, new_key in convert_dict.items():
        for command in commands:
            tex_content = re.sub(r"(\\"+command+r"*\{[^\{\}]*)\b"+old_key+r"\b([^e\{\}]*)", r"\1"+new_key+r"\2", tex_content)
    
    with open(new_tex_file, "w") as f:
        f.write(tex_content)

if __name__ == "__main__":
    old_bibtex = "extra_refs.bib"
    new_bibtex = "new.bib"
    tex_file = "main.tex"
    new_tex_file = "new_main.tex"
    main(old_bibtex, new_bibtex, tex_file, new_tex_file)
