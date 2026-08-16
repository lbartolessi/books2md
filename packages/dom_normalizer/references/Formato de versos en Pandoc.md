# Formato de poesía en verso para convertir con Pandoc

Para que Pandoc convierta poemas de forma limpia a Markdown conservando la estructura de los versos y las indentaciones espaciales (como los versos escalonados tras una cesura o punto), el objetivo ideal no es un párrafo estándar ni una cita (`>`), sino la extensión nativa de Pandoc llamada **Line Blocks** (Bloques de líneas).

En Markdown, los *Line blocks* se representan con una barra vertical (`|`) al inicio de cada línea. Esta sintaxis respeta los saltos de línea duros y, crucialmente, **conserva los espacios en blanco iniciales**.

Para lograr esto desde HTML, necesitas estructurar el código de una manera muy específica que el *parser* de Pandoc reconoce de forma nativa.

## 1. La Estructura HTML Requerida

Pandoc busca específicamente la clase `<div class="line-block">`. Todo lo que esté dentro de este contenedor será tratado como un bloque de líneas. Los saltos de verso deben marcarse con `<br />`.

Para la indentación del verso escalonado, los espacios normales (` `) corren el riesgo de ser colapsados por el motor de renderizado HTML antes de que Pandoc los procese. La forma más robusta y mecánicamente segura de forzar la indentación es utilizar **espacios de no separación** (`&nbsp;`) o **espacios largos** (como el *em space* `&#8195;`).

Aquí tienes la estructura exacta:

```html
<div class="line-block">
Este es el primer verso del poema,<br />
y aquí termina el segundo con un punto.<br />
&#8195;&#8195;&#8195;&#8195;Y aquí el verso continúa indentado,<br />
alineándose visualmente donde terminó el anterior.
</div>

```

## 2. El Resultado en Markdown (Salida de Pandoc)

Cuando ejecutas Pandoc sobre ese HTML (por ejemplo, con `pandoc -f html -t markdown`), la salida será la siguiente:

```markdown
| Este es el primer verso del poema,
| y aquí termina el segundo con un punto.
|     Y aquí el verso continúa indentado,
| alineándose visualmente donde terminó el anterior.

```

*Nota: Pandoc traducirá los `&#8195;` o `&nbsp;` a sus respectivos caracteres Unicode invisibles en el archivo Markdown resultante, lo cual mantendrá la indentación visual intacta para cualquier motor que renderice ese Markdown en el futuro.*

## 3. Estrategia para EPUBs y Automatización

Si estás extrayendo estos poemas de archivos de origen estructurados (como EPUBs o webs), te encontrarás con que la mayoría no usa `&nbsp;`, sino que usan márgenes CSS (ej. `<span style="margin-left: 3em;">...</span>` o `<p class="indent-2">`).

Dado que Pandoc ignora el CSS al convertir a Markdown, esa indentación se perderá a menos que intervengas el DOM antes de pasárselo a Pandoc.

La regla de transformación debería ser:

1. Identificar los contenedores de poemas (a menudo `<div class="poem">` o similar).
2. Envolverlos o renombrar su clase a `<div class="line-block">`.
3. Convertir los `<p>` de cada verso en texto seguido de `<br />`.
4. **Mapeo espacial:** Detectar reglas CSS de margen izquierdo (`margin-left` o `padding-left`) en las etiquetas anidadas e inyectar el número proporcional de `&nbsp;` o `&#8195;` directamente en el árbol de texto antes de entregárselo a Pandoc.

Para lograr esta transformación en tu pipeline, la estrategia consiste en buscar los contenedores de los poemas, iterar sobre sus versos para extraer las reglas CSS de margen o relleno, inyectar el número proporcional de espacios duros y, finalmente, reemplazar las etiquetas de bloque (`<p>` o `<div>`) por saltos de línea (`<br/>`).

Aquí tienes un script robusto utilizando `BeautifulSoup` y el analizador `"html5lib"` para garantizar el máximo cumplimiento con los estándares HTML, algo crucial al limpiar la estructura de libros digitales.

## El Script de Transformación

```python
from bs4 import BeautifulSoup
import re

def normalize_poem_indentations(html_content):
    # Utilizamos "html5lib" para asegurar un parseo estricto y tolerante a fallos
    # típicos de la estructura del DOM en los EPUBs.
    soup = BeautifulSoup(html_content, '"html5lib"')
    
    # 1. Identificar el contenedor del poema
    # (En los EPUBs suelen usar clases como 'poem', 'poetry', 'verse', etc.)
    poem_containers = soup.find_all(['div', 'section'], class_=re.compile(r'poem|poetry|verse', re.I))
    
    for container in poem_containers:
        # Cambiamos la clase para que Pandoc la reconozca como Line Block
        container['class'] = 'line-block'
        
        # 2. Buscar todos los versos (suelen ser <p> o <div> internos)
        verses = container.find_all(['p', 'div'])
        
        for verse in verses:
            # Evitar procesar el propio contenedor si la búsqueda es recursiva
            if verse == container:
                continue
                
            inline_style = verse.get('style', '')
            indent_spaces = ""
            
            # 3. Detectar y calcular la indentación
            if inline_style:
                # Buscamos margin-left o padding-left
                match = re.search(r'(?:margin|padding)-left:\s*([0-9.]+)(em|px|rem|%)', inline_style)
                if match:
                    value = float(match.group(1))
                    unit = match.group(2)
                    
                    # Mapeo a espacios de no separación (\xA0 es &nbsp; en Python)
                    # Asumimos que 1 'em' equivale aproximadamente a 4 espacios duros
                    if unit in ['em', 'rem']:
                        num_spaces = int(round(value * 4))
                    elif unit == 'px':
                        num_spaces = int(round((value / 16) * 4)) # Asumiendo 16px por em
                    else:
                        num_spaces = 2 # Valor por defecto para % u otros
                        
                    indent_spaces = '\xA0' * num_spaces
            
            # 4. Inyectar los espacios al inicio del texto del verso
            if indent_spaces:
                verse.insert(0, indent_spaces)
            
            # 5. Añadir <br/> al final y eliminar la etiqueta de bloque
            br_tag = soup.new_tag('br')
            verse.append(br_tag)
            
            # unwrap() elimina la etiqueta <p> o <div> pero conserva todo su contenido
            # (texto, spans interiores, y el <br/> que acabamos de añadir)
            verse.unwrap()

    # Devolvemos solo el contenido del body para evitar las etiquetas <html> 
    # que "html5lib" inyecta automáticamente.
    return soup.body.decode_contents()

# --- Ejemplo de uso ---
html_epub = """
<div class="poem">
    <p>La princesa está triste... ¿qué tendrá la princesa?</p>
    <p>Los suspiros se escapan de su boca de fresa,</p>
    <p style="margin-left: 2em;">que ha perdido la risa, que ha perdido el color.</p>
    <p style="margin-left: 4.5em;">La princesa está pálida en su silla de oro,</p>
</div>
"""

html_limpio = normalize_poem_indentations(html_epub)
print(html_limpio)

```

## Notas sobre el diseño del pipeline

1. **`unwrap()` es tu mejor aliado:** En lugar de extraer el texto (lo cual destruiría etiquetas internas útiles como `<i>` o `<em>` para cursivas), `unwrap()` disuelve el "envoltorio" del párrafo pero deja intacto el árbol interior, manteniéndolo en el flujo del `line-block`.
2. **Uso de `\xA0` vs `&nbsp;`:** BeautifulSoup maneja las entidades HTML convirtiéndolas automáticamente a sus caracteres Unicode correspondientes al parsear. Inyectar directamente `\xA0` (el carácter unicode para *Non-Breaking Space*) es más seguro en Python que inyectar el string literal `&nbsp;`, ya que evita que BS4 lo escape accidentalmente a `&amp;nbsp;`.
3. **Mapeo de Clases CSS externas:** El código anterior asume estilos en línea (`style="..."`). Si los EPUBs que procesas dependen de una hoja de estilos y usan clases como `<p class="indent-2">`, puedes añadir una condición extra antes del bloque de estilos:

```python
verse_classes = verse.get('class', [])
for cls in verse_classes:
    if 'indent-' in cls:
        # Extraer el número de la clase (ej. indent-2 -> 2)
        multiplier = int(''.join(filter(str.isdigit, cls)))
        indent_spaces = '\xA0' * (multiplier * 2) 

```
