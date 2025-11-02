import os
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pypdf import PdfReader, PdfWriter
import io # Necessário para BytesIO
import sys # Para sys._MEIPASS e sys.frozen

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue") # Mantido conforme sua última versão

# Função auxiliar para encontrar o Ghostscript
def get_ghostscript_path():
    gs_exe_name = "gswin64c.exe"  # Foco em Windows 64-bit

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    local_gs_path = os.path.join(base_dir, "gs", "bin", gs_exe_name)
    
    if os.path.exists(local_gs_path):
        return local_gs_path
    else:
        return gs_exe_name

def compress_pdf(input_path, progress_bar):
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_Comprimido{ext}"
    
    gs_command = get_ghostscript_path()

    try:
        progress_bar.configure(mode="indeterminate")
        progress_bar.start()
        subprocess.run([
            gs_command,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",
            "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={output_path}",
            input_path
        ], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        progress_bar.stop()
        progress_bar.configure(mode="determinate")
        progress_bar.set(0)
        return output_path
    except FileNotFoundError:
        progress_bar.stop()
        progress_bar.configure(mode="determinate")
        progress_bar.set(0)
        if gs_command == "gswin64c.exe":
            messagebox.showerror("Erro", "Ghostscript (gswin64c) não encontrado. Verifique se está instalado e no PATH do sistema.")
        else:
            messagebox.showerror("Erro", f"Ghostscript não encontrado no local esperado ({os.path.dirname(gs_command)}). A instalação da aplicação pode estar corrompida ou incompleta.")
        return None
    except subprocess.CalledProcessError as e:
        progress_bar.stop()
        progress_bar.configure(mode="determinate")
        progress_bar.set(0)
        messagebox.showerror("Erro", f"Erro ao comprimir PDF: {e}")
        return None

def split_pdf_by_pages(input_pdf_path, output_folder, pages_per_split, original_file_basename, progress_callback=None):
    try:
        reader = PdfReader(input_pdf_path)
        total_pages = len(reader.pages)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if total_pages == 0:
            messagebox.showinfo("Info", "O PDF está vazio. Nenhum arquivo foi criado.")
            if progress_callback: progress_callback(1.0)
            return

        total_parts = (total_pages + pages_per_split - 1) // pages_per_split
        file_counter = 0

        for i in range(0, total_pages, pages_per_split):
            writer = PdfWriter()
            for page_num in range(i, min(i + pages_per_split, total_pages)):
                writer.add_page(reader.pages[page_num])

            output_file = os.path.join(
                output_folder,
                f"{original_file_basename}_{file_counter + 1}.pdf"
            )
            with open(output_file, "wb") as f:
                writer.write(f)
            file_counter += 1

            if progress_callback:
                progress_callback(file_counter / total_parts)

        messagebox.showinfo("Sucesso", f"{file_counter} arquivos criados em '{output_folder}'.")
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao dividir o PDF por páginas: {e}")
        if progress_callback: progress_callback(0)

def split_pdf_by_size(input_pdf_path, output_folder, max_size_mb, original_file_basename, progress_callback=None):
    try:
        reader = PdfReader(input_pdf_path)
        total_pages = len(reader.pages)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if total_pages == 0:
            messagebox.showinfo("Info", "O PDF está vazio. Nenhum arquivo foi criado.")
            if progress_callback: progress_callback(1.0)
            return

        target_size_bytes = max_size_mb * 1024 * 1024
        output_file_counter = 0
        
        pages_for_current_pdf_part = []

        for page_idx in range(total_pages):
            current_page_object = reader.pages[page_idx]
            
            potential_pages_for_part = pages_for_current_pdf_part + [current_page_object]
            
            temp_writer_for_check = PdfWriter()
            for p_obj in potential_pages_for_part:
                temp_writer_for_check.add_page(p_obj)
            
            with io.BytesIO() as temp_buffer_for_check:
                temp_writer_for_check.write(temp_buffer_for_check)
                size_of_potential_part = temp_buffer_for_check.getbuffer().nbytes
            
            if size_of_potential_part > target_size_bytes:
                if pages_for_current_pdf_part: 
                    writer_to_save_old_part = PdfWriter()
                    for p_obj_old in pages_for_current_pdf_part:
                        writer_to_save_old_part.add_page(p_obj_old)
                    
                    output_file_counter += 1
                    output_file = os.path.join(output_folder, f"{original_file_basename}_{output_file_counter}.pdf")
                    with open(output_file, "wb") as f:
                        writer_to_save_old_part.write(f)
                    
                    pages_for_current_pdf_part = [current_page_object] 
                else: 
                    output_file_counter += 1
                    output_file = os.path.join(output_folder, f"{original_file_basename}_{output_file_counter}.pdf")
                    with open(output_file, "wb") as f:
                        temp_writer_for_check.write(f)
                    
                    pages_for_current_pdf_part = [] 
            else: 
                pages_for_current_pdf_part.append(current_page_object)

            if progress_callback:
                progress_callback((page_idx + 1) / total_pages) 

        if pages_for_current_pdf_part:
            final_writer = PdfWriter()
            for p_obj_final in pages_for_current_pdf_part:
                final_writer.add_page(p_obj_final)
            
            output_file_counter += 1
            output_file = os.path.join(output_folder, f"{original_file_basename}_{output_file_counter}.pdf")
            with open(output_file, "wb") as f:
                final_writer.write(f)
        
        if output_file_counter > 0:
            messagebox.showinfo("Sucesso", f"{output_file_counter} arquivos criados em '{output_folder}' (dividido por tamanho).")
        elif total_pages > 0 : 
             messagebox.showinfo("Info", f"O PDF original ({total_pages} pág.) é menor que o limite de {max_size_mb}MB. Um único arquivo foi criado ou nenhuma divisão foi necessária se já era um único arquivo.")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro ao dividir o PDF por tamanho: {e}")
        if progress_callback: progress_callback(0)

def escolher_arquivo():
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        entry_pdf.set(file_path)

def escolher_pasta_saida():
    pasta = filedialog.askdirectory()
    if pasta:
        entry_saida.set(pasta)

def update_split_options(*args):
    mode = split_mode_var.get()
    if mode == "Por Páginas":
        entry_paginas_widget.configure(state="normal")
        entry_tamanho_mb_widget.configure(state="disabled")
    elif mode == "Por Tamanho (MB)":
        entry_paginas_widget.configure(state="disabled")
        entry_tamanho_mb_widget.configure(state="normal")

def iniciar():
    caminho_pdf_original = entry_pdf.get()
    pasta_saida_local = entry_saida.get() or "pdfs_divididos_e_comprimidos" 
    modo_divisao = split_mode_var.get()

    if not caminho_pdf_original or not os.path.exists(caminho_pdf_original):
        messagebox.showwarning("Aviso", "Selecione um arquivo PDF válido.")
        return

    if modo_divisao == "Por Páginas":
        try:
            paginas_por_arquivo = int(entry_paginas.get())
            if paginas_por_arquivo <= 0:
                messagebox.showwarning("Aviso", "O número de páginas por arquivo deve ser maior que zero.")
                return
        except ValueError:
            messagebox.showwarning("Aviso", "Informe um número válido de páginas por arquivo.")
            return
    elif modo_divisao == "Por Tamanho (MB)":
        try:
            tamanho_max_mb = float(entry_tamanho_mb.get())
            if tamanho_max_mb <= 0:
                messagebox.showwarning("Aviso", "O tamanho máximo por arquivo deve ser maior que zero MB.")
                return
        except ValueError:
            messagebox.showwarning("Aviso", "Informe um tamanho máximo válido em MB (ex: 5 ou 4.5).")
            return
            
    btn_iniciar.configure(state="disabled")
    status_label_var.set("Processo em andamento, aguarde...") 
    progress_bar.set(0) 

    # <<< INÍCIO DAS MODIFICAÇÕES NA FUNÇÃO TASK >>>
    def task():
        caminho_pdf_comprimido_para_deletar = None 
        task_flow_initiated = False 
        try:
            original_file_basename = os.path.splitext(os.path.basename(caminho_pdf_original))[0]
            
            status_label_var.set("Comprimindo PDF...")
            # app.update_idletasks() # Opcional, geralmente não necessário para StringVar em thread com CTk

            caminho_pdf_comprimido = compress_pdf(caminho_pdf_original, progress_bar)
            
            if caminho_pdf_comprimido and os.path.exists(caminho_pdf_comprimido):
                caminho_pdf_comprimido_para_deletar = caminho_pdf_comprimido 
                task_flow_initiated = True 

                status_label_var.set("Dividindo PDF...")
                progress_bar.set(0) 

                if modo_divisao == "Por Páginas":
                    num_paginas = int(entry_paginas.get()) 
                    split_pdf_by_pages(caminho_pdf_comprimido, pasta_saida_local, num_paginas, original_file_basename, progress_callback=progress_bar.set)
                elif modo_divisao == "Por Tamanho (MB)":
                    max_mb = float(entry_tamanho_mb.get()) 
                    split_pdf_by_size(caminho_pdf_comprimido, pasta_saida_local, max_mb, original_file_basename, progress_callback=progress_bar.set)
            
            elif caminho_pdf_comprimido and not os.path.exists(caminho_pdf_comprimido):
                 messagebox.showwarning("Aviso Interno", f"Arquivo comprimido '{os.path.basename(caminho_pdf_comprimido)}' não foi encontrado para divisão. Não será deletado.")
                 caminho_pdf_comprimido_para_deletar = None 
            elif not caminho_pdf_comprimido:
                # compress_pdf retornou None, sua própria função já mostrou o erro.
                # task_flow_initiated permanece False.
                pass
        
        except Exception as e_task: # Captura exceções mais amplas na tarefa
            task_flow_initiated = True # A tarefa iniciou mas pode ter falhado
            messagebox.showerror("Erro na Tarefa Principal", f"Ocorreu um erro inesperado durante o processamento principal:\n{e_task}")
        finally: 
            if caminho_pdf_comprimido_para_deletar and os.path.exists(caminho_pdf_comprimido_para_deletar):
                status_label_var.set("Limpando arquivo intermediário...")
                try:
                    os.remove(caminho_pdf_comprimido_para_deletar)
                except OSError as e_remove:
                    messagebox.showwarning("Erro de Limpeza", f"Não foi possível remover o arquivo intermediário '{os.path.basename(caminho_pdf_comprimido_para_deletar)}':\n{e_remove}")
            
            btn_iniciar.configure(state="normal")

            if task_flow_initiated: 
                status_label_var.set("Processo finalizado.")
            else: 
                status_label_var.set("Processo não iniciado ou falhou na compressão.")
            
            # Limpa a mensagem de status após alguns segundos
            app.after(4000, lambda: status_label_var.set(""))
    # <<< FIM DAS MODIFICAÇÕES NA FUNÇÃO TASK >>>
    
    threading.Thread(target=task, daemon=True).start()


# --- GUI ---
# (O restante da sua GUI permanece o mesmo que você forneceu)
app = ctk.CTk()
app.title("Compressor e Divisor de PDF")
app.geometry("600x400") # Mantido conforme sua última versão
app.resizable(False, False)

main_frame = ctk.CTkFrame(app)
main_frame.pack(padx=10, pady=10, fill="both", expand=True)

ctk.CTkLabel(main_frame, text="Arquivo PDF:").grid(row=0, column=0, padx=5, pady=(10,5), sticky="e")
entry_pdf = ctk.StringVar()
ctk.CTkEntry(main_frame, textvariable=entry_pdf, width=350).grid(row=0, column=1, padx=5, pady=(10,5), sticky="ew")
ctk.CTkButton(main_frame, text="Selecionar Arquivo", command=escolher_arquivo).grid(row=0, column=2, padx=5, pady=(10,5))

ctk.CTkLabel(main_frame, text="Pasta de Saída:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
entry_saida = ctk.StringVar()
ctk.CTkEntry(main_frame, textvariable=entry_saida, width=350, placeholder_text="Opcional (padrão: pdfs_divididos_e_comprimidos)").grid(row=1, column=1, padx=5, pady=5, sticky="ew")
ctk.CTkButton(main_frame, text="Selecionar Pasta", command=escolher_pasta_saida).grid(row=1, column=2, padx=5, pady=5)

ctk.CTkLabel(main_frame, text="Modo de Divisão:").grid(row=2, column=0, padx=5, pady=(15,5), sticky="e")
split_mode_var = ctk.StringVar(value="Por Páginas")
split_mode_button = ctk.CTkSegmentedButton(main_frame, values=["Por Páginas", "Por Tamanho (MB)"],
                                           variable=split_mode_var,
                                           command=update_split_options)
split_mode_button.grid(row=2, column=1, columnspan=2, padx=5, pady=(15,5), sticky="w")

ctk.CTkLabel(main_frame, text="Páginas por arquivo:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
entry_paginas = ctk.StringVar(value="") 
entry_paginas_widget = ctk.CTkEntry(main_frame, textvariable=entry_paginas, width=100)
entry_paginas_widget.grid(row=3, column=1, padx=5, pady=5, sticky="w")

ctk.CTkLabel(main_frame, text="Tamanho máx. (MB):").grid(row=4, column=0, padx=5, pady=5, sticky="e")
entry_tamanho_mb = ctk.StringVar(value="") 
entry_tamanho_mb_widget = ctk.CTkEntry(main_frame, textvariable=entry_tamanho_mb, width=100)
entry_tamanho_mb_widget.grid(row=4, column=1, padx=5, pady=5, sticky="w")

progress_bar = ctk.CTkProgressBar(main_frame, width=400, mode="determinate") 
progress_bar.grid(row=5, column=0, columnspan=3, padx=15, pady=(20,5)) 
progress_bar.set(0)

btn_iniciar = ctk.CTkButton(main_frame, text="Iniciar", command=iniciar, height=40) 
btn_iniciar.grid(row=6, column=0, columnspan=3, pady=(10,5)) 

status_label_var = ctk.StringVar(value="")
status_label = ctk.CTkLabel(main_frame, textvariable=status_label_var, text_color="gray") 
status_label.grid(row=7, column=0, columnspan=3, pady=(0, 5))


signature_font = ctk.CTkFont(slant="italic", size=9) 
signature_label = ctk.CTkLabel(main_frame, text="By Felipe Freitas", font=signature_font, text_color="gray")
# Mantido o pady da assinatura conforme sua última versão
signature_label.grid(row=8, column=1, columnspan=2, padx=5, pady=(30,5), sticky="se") 


main_frame.grid_columnconfigure(1, weight=1)

update_split_options()

app.mainloop()
