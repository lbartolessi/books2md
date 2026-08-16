# IDEAS para la heurística de descubrimiento de bloques block-line

Dado que el atributo `epub:type` contiene dos puntos (`:`), no podemos buscarlo usando la sintaxis básica de argumentos de BeautifulSoup. Además, queremos que esta regla sea un "OR" lógico: que atrape el contenedor si tiene la clase CSS correcta **o** si tiene el atributo `epub:type="z3998:poem"`.

La forma más elegante y robusta de hacer esto en BeautifulSoup es pasarle una función de evaluación personalizada a `find_all()`. De paso, solucionaremos el problema del anidamiento (el `>` del `blockquote` en Markdown) forzando que cualquier contenedor detectado se transforme en un simple `<div>`.

Aquí tienes cómo modificar esa sección de tu script:

## 1. La Función de Evaluación

Define esta función antes de tu bucle principal. Actuará como un filtro estricto que BeautifulSoup aplicará a cada etiqueta del DOM:

```python
import re

def is_poem_container(tag):
    # 1. Prioridad absoluta: Estándar semántico de EPUB (ignora si la clase está corrupta)
    if tag.get('epub:type') == 'z3998:poem':
        return True
    
    # 2. Respaldo: Búsqueda por clases CSS habituales
    classes = tag.get('class')
    if classes:
        # Unimos las clases por si hay múltiples (ej. class="layout-modern poetry")
        class_str = ' '.join(classes)
        if re.search(r'poem|poetry|verse', class_str, re.I):
            return True
            
    return False

```

## 2. Integración y mutación de la etiqueta

Ahora, reemplazamos tu antigua búsqueda por la nueva función y añadimos una línea crucial (`container.name = 'div'`) para evitar que Pandoc herede formatos no deseados como las citas (`blockquote`).

```python
    # Usamos la función de evaluación
    poem_containers = soup.find_all(is_poem_container)
    
    for container in poem_containers:
        # --- EL TRUCO ESTRUCTURAL ---
        # Convertimos la etiqueta original (sea blockquote, table, section...) 
        # en un div estándar. Esto evita que Pandoc añada marcadores como el ">"
        container.name = 'div'
        
        # Sobrescribimos todas las clases (eliminando las corruptas o inútiles)
        # por la única que Pandoc necesita.
        container['class'] = 'line-block'
        
        # Opcional: limpiar atributos residuales del EPUB para no arrastrar basura
        if 'epub:type' in container.attrs:
            del container['epub:type']
            
        # 2. Buscar todos los versos (el resto de tu lógica se mantiene igual)
        verses = container.find_all(['p', 'div', 'tr']) # Añadido 'tr' por si vienen de tablas
        
        for verse in verses:
            if verse == container:
                continue
            
            # ... [Aquí va tu lógica de limpieza de espacios e inyección de <br/>] ...

```

## ¿Por qué esto soluciona el fallo de Standard Ebooks?

* **Cortocircuito semántico:** En el caso `StandardEbooks_Caso_Estructural`, aunque la clase sea `clase-modificada`, la función `is_poem_container` lee `epub:type="z3998:poem"`, devuelve `True` inmediatamente y captura el nodo.
* **Transmutación de Nodos (`container.name = 'div'`):** En lugar de intentar disolver el `blockquote` con `.unwrap()` (lo cual es arriesgado si es el nodo raíz), simplemente le decimos a BeautifulSoup que esa etiqueta ahora se llama `div`.
* **Purga de clases (`container['class'] = 'line-block'`):** Al asignar el valor directamente (en lugar de hacer `append`), destruyes la `clase-modificada` y dejas un `<div class="line-block">` puro e inmaculado, que es exactamente lo que el analizador de Pandoc espera para generar la sintaxis con barras verticales `|`.

El atributo `epub:type` pertenece al estándar EPUB 3, pero la inmensa mayoría de libros digitales provienen del estándar EPUB 2 o son conversiones automáticas hechas con herramientas que barren por completo la semántica original.

Cuando nos quedamos a ciegas sin el atributo oficial, tenemos que recurrir a una estrategia de "defensa en profundidad" dentro de tu función `is_poem_container`. Si falla el primer filtro, pasamos al siguiente.

Aquí tienes cómo estructurar esta red de seguridad en tres niveles:

## Nivel 1: Ampliar la red semántica (Clases CSS)

Dado que estás procesando textos multilingües, la palabra `poem` no será suficiente. Debemos ampliar la expresión regular para atrapar la terminología habitual de las editoriales en español, inglés o francés, así como términos estructurales.

## Nivel 2: Análisis de la "Forma" del DOM (Duck Typing)

Si no hay clases, o están ofuscadas (como `<div class="calibre1">`), tenemos que fijarnos en cómo se comporta el contenedor. *"Si tiene forma de poema y saltos de línea de poema, es un poema"*.
Los patrones estructurales más comunes de los versos "huérfanos" son:

1. Un párrafo (`<p>`) o caja (`<div>`) que contiene una alta densidad de etiquetas `<br/>` directas.
2. Una tabla (`<table>`) donde todas sus filas (`<tr>`) tienen exactamente una sola celda (`<td>`). (Esto atrapa tu caso `Library_Of_America_Caso_Estructural`).

### Código: La Heurística Completa

Aquí tienes la función de evaluación blindada con estas alternativas:

```python
import re

def is_poem_container(tag):
    # ---------------------------------------------------------
    # 1. EL ESTÁNDAR DE ORO
    # ---------------------------------------------------------
    if tag.get('epub:type') == 'z3998:poem':
        return True

    # ---------------------------------------------------------
    # 2. HEURÍSTICA SEMÁNTICA (Clases CSS multi-idioma)
    # ---------------------------------------------------------
    classes = tag.get('class')
    if classes:
        class_str = ' '.join(classes)
        # Buscamos términos comunes en edición poética o teatral
        # (Añade o quita términos según los libros que proceses)
        regex_poesia = r'poem|poetry|verse|stanza|poema|estrofa|verso|canto|lyric'
        if re.search(regex_poesia, class_str, re.I):
            return True

    # ---------------------------------------------------------
    # 3. HEURÍSTICA ESTRUCTURAL (La forma del nodo)
    # ---------------------------------------------------------
    
    # Caso A: Densidad de saltos de línea (Típico de Calibre)
    # Buscamos si el elemento tiene múltiples <br/> en su primer nivel.
    # Un párrafo normal de texto rara vez tiene más de 1 o 2 <br/> directos.
    if tag.name in ['p', 'div']:
        # Contamos los <br/> que son hijos directos del contenedor
        br_directos = len(tag.find_all('br', recursive=False))
        if br_directos >= 2: 
            return True

    # Caso B: Tablas de un solo bloque (Típico de formatos antiguos)
    # Una tabla usada para alinear un poema suele tener múltiples filas,
    # pero solo una columna de datos.
    if tag.name == 'table':
        filas = tag.find_all('tr')
        if filas:
            # Comprobamos si todas las filas tienen exactamente 1 <td> y ningún <th>
            es_tabla_poema = all(
                len(fila.find_all('td', recursive=False)) == 1 and 
                len(fila.find_all('th', recursive=False)) == 0 
                for fila in filas
            )
            # Solo si tiene más de una fila y cumple la regla de la columna única
            if len(filas) > 1 and es_tabla_poema:
                return True

    # Si no cumple ninguno de los filtros, lo descartamos
    return False

```

## ⚠️ La advertencia de los "Falsos Positivos"

Al habilitar la heurística estructural (Nivel 3), tu script se vuelve mucho más inteligente, pero también asumes un riesgo: **los falsos positivos**.

Con la regla de la densidad de `<br/>`, el script podría convertir accidentalmente en `line-block` cosas como:

* La página de dedicatoria del libro.
* La dirección postal de la editorial en la página de créditos.
* Una carta ficticia insertada dentro de una novela.

Afortunadamente, para Pandoc (y visualmente en Markdown), un bloque de líneas (`|`) aplicado a una dirección postal o a una dedicatoria no es destructivo, de hecho, conservará el formato visual correctamente.

epub:type="z3998:poem" va a ser raro encontrarlo en los epubs y en ningún caso va a existir cuando se trate de html de una web. Los nombres de clase tienen cuatro problemas: 1 que no suelen asignarse con criterios semánticos sino como apoyo a las hojas de estilo (.calibre_345678, por ejemplo). 2 que pueden ser varias las palabras empleadas (solo en español podrían ser: poesía, poema, verso, estrofa, estancia, soneto, decima, redondilla, romance... etc, más plurales más sinónimos. 3. Estas palabras pueden estar en cualquier idioma, no necesariamente en el idioma del libro y 4. Pueden ser parte de un nombre complejo (verso_italic_capital, poema_bold, etc...). Podríamos asumir que estamos tratando con una estructura formal line-block que puede ser tanto un poema de gran intensidad lírica como una prosaica lista de la lavandería y dejar a las aplicaciones que usen el markdown (RAG, ereaders, etc.) la tarea de determinar su semántica.

Es un planteamiento impecable y arquitectónicamente mucho más robusto. Al intentar cazar la intención semántica a través de clases CSS caóticas, ofuscadas (como las de Calibre) o dependientes del idioma, nos estábamos metiendo en un pozo sin fondo de expresiones regulares inestables.

Reducir el problema a su dimensión estrictamente formal es la decisión correcta. Un `line-block` (`|`) en Markdown es, en esencia, solo eso: **texto con saltos de línea duros forzados intencionalmente**. Delegar el análisis de si ese texto es un soneto o una factura de lavandería a los sistemas posteriores (un motor de búsqueda semántica, un RAG o un modelo de inferencia) limpia las responsabilidades del script de extracción.

Si abandonamos el diccionario de sinónimos y nos pasamos a una heurística 100% estructural (duck typing puro), la función de evaluación de BeautifulSoup se vuelve mucho más rápida, determinista y agnóstica al idioma.

Aquí tienes cómo quedaría esa lógica de detección puramente formal:

```python
def is_line_block_structure(tag):
    """
    Evalúa si un contenedor tiene la estructura mecánica de un line-block,
    ignorando por completo su clase CSS o contenido semántico.
    """
    # 1. EVITAR FALSOS POSITIVOS BÁSICOS
    # No evaluamos etiquetas que por naturaleza ya son estructuradas o en línea
    if tag.name in ['span', 'a', 'b', 'i', 'em', 'strong', 'sup', 'sub']:
        return False

    # 2. HEURÍSTICA DE SALTOS DE LÍNEA EXPLICITOS (<br/>)
    if tag.name in ['p', 'div', 'blockquote']:
        # Contamos los saltos de línea directos.
        # Un párrafo normal rara vez tiene 2 o más <br/> consecutivos o sueltos
        # que dividan el texto en múltiples líneas cortas.
        br_directos = len(tag.find_all('br', recursive=False))
        if br_directos >= 2:
            return True

    # 3. HEURÍSTICA TABULAR (Rejillas de alineación)
    if tag.name == 'table':
        filas = tag.find_all('tr', recursive=False)
        # Si la tabla tiene cuerpos (tbody), buscamos ahí
        if not filas:
            tbody = tag.find('tbody')
            if tbody:
                filas = tbody.find_all('tr', recursive=False)

        if filas:
            # Una tabla que actúa como bloque de líneas suele tener
            # varias filas, pero estrictamente UNA sola columna (sin cabeceras)
            es_columna_unica = all(
                len(fila.find_all('td', recursive=False)) == 1 and 
                len(fila.find_all('th', recursive=False)) == 0 
                for fila in filas
            )
            if len(filas) > 1 and es_columna_unica:
                return True

    # 4. HEURÍSTICA DEL ESTÁNDAR EPUB (Por si acaso existe)
    # Sigue siendo un indicador mecánico incuestionable del formato deseado,
    # aunque sea raro encontrarlo.
    if tag.get('epub:type') == 'z3998:poem':
        return True

    return False

```

## El desafío de la "Fragmentación de Bloques"

Esta aproximación resuelve el problema de las clases, pero abre un nuevo frente de batalla puramente formal.

A veces, el maquetador del EPUB no utiliza `<br/>` dentro de un contenedor grande, sino que convierte cada línea en un párrafo independiente, forzando los márgenes a cero para que visualmente parezcan un bloque continuo:

```html
<div class="contenedor-indescifrable">
  <p>Canta, oh musa...</p>
  <p>la cólera del pélida Aquiles;</p>
  <p>cólera funesta que causó...</p>
</div>

```

Nuestra heurística actual ignorará esto porque no hay etiquetas `<br/>`, y Pandoc lo renderizará como tres párrafos separados por líneas en blanco, perdiendo la estructura de `line-block`.

¡Manos a la obra! Para que el motor de extracción no deje atrás estos versos fragmentados en sus conversiones a Markdown, necesitamos cambiar el enfoque de evaluación.

En lugar de mirar los nodos individualmente o evaluar a un "padre" de forma global (un `<div>` podría contener un poema de 4 líneas y luego 20 párrafos de texto normal), la topología más eficiente es buscar **secuencias de hermanos** (*sibling clusters*).

La regla sería: *"Si encontramos una sucesión ininterrumpida de N párrafos o bloques y su longitud máxima no excede X caracteres, los agrupamos, los envolvemos en un `<div class="line-block">` y disolvemos sus etiquetas originales"*.

### La Topología de Agrupación de Hermanos

Aquí tienes la función diseñada para ejecutarse como un pase de saneamiento en el árbol DOM. Evaluará secuencias consecutivas y las fusionará.

```python
from bs4 import BeautifulSoup

def consolidate_fragmented_line_blocks(soup, min_sequence=3, max_chars_per_line=85):
    """
    Rastrea el DOM buscando secuencias de párrafos cortos consecutivos 
    y los consolida en un único contenedor line-block.
    """
    # Buscamos en todos los posibles contenedores estructurales
    for parent in soup.find_all(['div', 'section', 'blockquote', 'body']):
        
        # Iteramos solo sobre los hijos directos para evaluar la adyacencia real
        children = parent.find_all(recursive=False)
        sequence = []
        
        # Función interna para mutar el DOM una vez hallada una secuencia válida
        def process_sequence(seq):
            if len(seq) >= min_sequence:
                # Comprobamos que TODOS los elementos de la secuencia sean "cortos".
                # (Se podría relajar usando un promedio si hay versos excepcionalmente largos)
                is_short_block = all(
                    len(node.get_text(strip=True)) <= max_chars_per_line 
                    for node in seq
                )
                
                if is_short_block:
                    # 1. Creamos el nuevo contenedor line-block
                    wrapper = soup.new_tag('div')
                    wrapper['class'] = 'line-block'
                    
                    # 2. Lo insertamos en el DOM justo antes del primer verso de la secuencia
                    seq[0].insert_before(wrapper)
                    
                    # 3. Trasladamos los nodos al nuevo envoltorio y preparamos el Markdown
                    for node in seq:
                        # Inyectamos el salto de línea duro al final
                        br_tag = soup.new_tag('br')
                        node.append(br_tag)
                        
                        # Movemos el nodo dentro del line-block
                        wrapper.append(node)
                        
                        # Disolvemos el <p> o <div> original, dejando el texto y el <br/>
                        node.unwrap()
            
            # Vaciamos la lista para empezar a buscar la siguiente secuencia
            seq.clear()

        # Bucle de evaluación topológica
        for child in children:
            # Solo consideramos nodos de bloque típicos
            if child.name in ['p', 'div']:
                text_len = len(child.get_text(strip=True))
                
                # Descartamos párrafos totalmente vacíos para no romper la secuencia,
                # pero tampoco los metemos en el line-block.
                if text_len > 0:
                    sequence.append(child)
                else:
                    # Un párrafo vacío rompe la secuencia (podría ser un cambio de sección)
                    process_sequence(sequence)
            else:
                # Cualquier otra etiqueta (un <h1>, un <ul>, un <hr>) rompe la racha
                process_sequence(sequence)
                
        # Al terminar de iterar los hijos del padre actual, procesamos lo que quede colgado
        process_sequence(sequence)

    return soup

```

## ¿Por qué esta arquitectura es sólida?

1. **Agnóstica a las Clases:** Le da exactamente igual si los párrafos se llaman `<p class="calibre_12">` o simplemente `<p>`. Se fija en la disposición mecánica de los elementos de la página.
2. **Protección del resto del libro:** Al exigir un mínimo de elementos consecutivos (`min_sequence=3`), evitas atrapar títulos aislados o epígrafes cortos. Al limitar los caracteres (`max_chars_per_line=85`, un poco más del ancho estándar histórico de 80 columnas), evitas atrapar diálogos largos, manteniendo los párrafos estándar de la novela o el ensayo intactos.
3. **Flujo de operaciones seguro:** El uso de `insert_before()` y luego `append()` mueve físicamente los nodos en el árbol de BeautifulSoup en tiempo de ejecución sin romper la iteración sobre la lista original `children`, la cual ya fue extraída.

## El orden en Books2MD

Si integras esto en tu pipeline, el orden de ejecución es crítico. Este saneamiento topológico debe ocurrir **después** de arreglar las notas al pie (para no romper las referencias), pero **antes** de buscar explícitamente clases CSS u otras heurísticas, ya que este paso genera los `<div class="line-block">` limpios que Pandoc devorará.

Es una excelente observación. Los diálogos a base de estricta stichomythia (intercambio rápido de réplicas cortas) encajarían peligrosamente en la métrica de nuestra topología de versos, convirtiendo una conversación de novela en un falso bloque de líneas poético.

Añadir un filtro que detecte los signos de diálogo (como el guion largo tradicional en español `—`, el guion corto `-`, o las comillas de diálogo angulares `«`) es la manera más limpia de blindar la heurística.

## El Filtro Anti-Diálogos

Podemos integrar una validación dentro de la función de evaluación de longitud o como un chequeo rápido antes de meter el nodo en la secuencia:

```python
import re

def is_dialogue_line(text):
    """
    Detecta si un párrafo comienza con marcas típicas de diálogo en narrativa.
    """
    # Patrón que busca guiones largos, cortos o comillas de diálogo al inicio (ignorando espacios iniciales)
    dialogue_pattern = r'^\s*(—|–|-|«|\"|\'|„)'
    return bool(re.match(dialogue_pattern, text))

```

## Integración en el Bucle Topológico

Modificamos el bloque donde evaluamos los hijos para que, si un párrafo comienza con marcas de diálogo, actúe de inmediato como un **elemento de ruptura** de la secuencia, exactamente igual que un título o un párrafo vacío:

```python
        for child in children:
            if child.name in ['p', 'div']:
                text = child.get_text()
                text_len = len(text.strip())
                
                # Si tiene contenido y NO es una línea de diálogo, lo acumulamos
                if text_len > 0 and not is_dialogue_line(text):
                    sequence.append(child)
                else:
                    # Si está vacío o es un diálogo, rompe la secuencia de versos
                    process_sequence(sequence)
            else:
                process_sequence(sequence)

```

Con este pequeño ajuste, garantizamos que los intercambios conversacionales rápidos queden completamente inmunes al barrido topológico, preservando la prosa narrativa tal y como fue concebida.
