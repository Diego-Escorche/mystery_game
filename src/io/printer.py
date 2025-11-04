from colorama import Fore, Style

def print_header(title: str):
    print(Style.BRIGHT + Fore.YELLOW + f"=== {title} ===")
    print(Fore.YELLOW + "Noche fría. Las lonas crujen. Un secreto bajo la carpa.")

def print_hint(text: str):
    print(Fore.GREEN + text)
