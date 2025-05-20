from PIL import Image
import os
import datetime

# Ruta a la carpeta donde están las imágenes
folder = "E:/GEX/GitHub/Gex-Repository/output"

# Filtrar imágenes solo del día actual
today = datetime.datetime.now().strftime("%Y%m%d")
images = sorted([
    img for img in os.listdir(folder)
    if img.endswith(".png") and today in img
])

# Verificación
if not images:
    print("No se encontraron imágenes para hoy.")
else:
    # Cargar las imágenes
    frames = [Image.open(os.path.join(folder, img)) for img in images]

    # Guardar como GIF animado
    output_path = os.path.join(folder, f"output_{today}.gif")
    frames[0].save(
        output_path,
        format='GIF',
        append_images=frames[1:],
        save_all=True,
        duration=300,  # milisegundos por frame
        loop=0
    )

    print(f"GIF creado: {output_path}")

    # Eliminar imágenes después de crear el GIF (opcional)
    #for img_name in images:
        #os.remove(os.path.join(folder, img_name))
    #print("Imágenes eliminadas.")