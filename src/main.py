import customtkinter
import chat_ui
import conversation_data

customtkinter.set_appearance_mode("Dark")

result = conversation_data.load_data()

if result == "missing":
    print("First launch: Creating Optimizer data file.")

    if conversation_data.save_data():
        print("Optimizer data initialized successfully.")
    else:
        print("Error creating Optimizer data file.")
        raise SystemExit(1)

elif result == "loaded":
    print("Optimizer data loaded successfully.")

elif result in ("invalid", "error"):
    print("Problem loading Optimizer data.")
    raise SystemExit(1)

optimizer = customtkinter.CTk()

optimizer.title("DI-ZONE Optimizer")
optimizer.geometry("1200x750")

optimizer.grid_rowconfigure(0, weight = 1)
optimizer.grid_columnconfigure(0, weight = 1)

chat_ui.show_chat_interface(optimizer)

optimizer.mainloop()