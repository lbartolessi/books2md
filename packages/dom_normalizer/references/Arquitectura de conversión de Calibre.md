# Arquitectura de conversión de Calibre

Este estudio de ingeniería inversa analiza en detalle cómo el motor de conversión y el componente `htmlwriter` de Calibre procesan, estructuran y degradan o refactorizan la semántica de los documentos procedentes de 17 formatos de origen al exportarlos a EPUB (XHTML/CSS).

La arquitectura de conversión de Calibre opera en tres etapas principales:

1. **Etapa de Descompilación/Extracción (Input Plugin):** Transmuta el formato propietario a una representación interna XHTML en memoria (OEB - *Open eBook*).

2. **Etapa de Transformación (OEB Transforms):** Normaliza y unifica la codificación de caracteres, reescala el árbol jerárquico de fuentes y aplica el motor de aplanado de CSS (*CSS flattening*), que inyecta clases autogeneradas secuencialmente bajo el patrón de nomenclatura de la clase `.calibreNN` (donde `NN` representa un entero correlativo).

3. **Etapa de Serialización (Output Plugin / htmlwriter):** Divide los archivos en bloques XHTML de tamaño controlado (`index_split_00X.xhtml`), resuelve enlaces internos y exporta la estructura final del EPUB.

A continuación se detalla la clasificación de las huellas dactilares (*fingerprints*) estructurales y el comportamiento de las notas al pie para los 17 formatos de origen, divididos en tres familias de linajes.

---

## 1. Linaje Fluido/Hipervinculado

**Formatos incluidos:** `.mobi`, `.azw`, `.azw3`, `.lit`, `.htmlz`, `.fbz`, `.prc`, `.kepub`.

### Análisis de Huellas Dactilares e Ingeniería Inversa

Este linaje proviene de formatos estructurados basados originalmente en HTML, esquemas XML dedicados (como FictionBook) o bases de datos con capacidad nativa de direccionamiento por desplazamiento de bytes (como Mobipocket/PalmDoc). Al pasar por el convertidor de Calibre, el comportamiento de las notas y enlaces se normaliza bajo un esquema plano de anclajes internos.

* **Estructura de Llamada de Nota:** Calibre suele transformar las llamadas de notas en elementos inline (muchas veces envueltos en etiquetas `<sup>` o directamente usando hipervínculos `<a>`) caracterizados por clases secuenciales. El destino de la referencia y el identificador de origen se resuelven mediante anclajes relativos.

* **Patrón de Identificadores (IDs):**
* **Llamadas en el cuerpo:** `id="calibre_link-NN"` o `id="note_id_NN"`.

* **Destinos en el cuerpo de notas:** `id="footnote_NN"` o `id="fn_NN"` o `id="note_NN"`.
* **Enlaces de retroceso (Backlinks):** Calibre añade un carácter de retorno de forma literal, habitualmente la flecha izquierda `←` o el símbolo `↩` con la clase `.backref`.

* **Aplanado CSS y calibreNN:** El motor de aplanado de CSS analiza todas las propiedades de estilo del formato de origen. Si detecta que un elemento de cita o nota al pie tiene una sangría o un tamaño de fuente específico, creará una nueva clase `.calibreNN` en el archivo `stylesheet.css` para cada variación menor, duplicando reglas y saturando el atributo `class` de las etiquetas de párrafo (`<p>`) y de texto inline (`<span>`).

#### Ejemplo de Estructura DOM resultante (MOBI/AZW3 a EPUB)

```html
<!-- En el archivo index_split_001.xhtml (Cuerpo Principal) -->
<p class="calibre12">
  El descubrimiento de la fisión nuclear en 1938
  <a class="calibre8" id="calibre_link-14" href="index_split_002.xhtml#note_id_1">[1]</a>
  revolucionó la física del siglo XX.
</p>

<!-- En el archivo index_split_002.xhtml (Sección de Notas / Cuerpos Separados) -->
<div class="calibre20" id="note_id_1">
  <p class="calibre21">
    <span class="calibre22">[1]</span> 
    Lise Meitner y Otto Frisch proporcionaron la primera explicación teórica de este fenómeno.
    <a class="calibre8" href="index_split_001.xhtml#calibre_link-14">↩</a>
  </p>
</div>

```

---

## 2. Linaje de Maquetación Fija o Fragmentada

**Formatos incluidos:** `.azw4`, `.chm`, `.lrf` (y conversiones destructivas desde PDF).

### Análisis de Huellas Dactilares e Ingeniería Inversa

Este linaje agrupa formatos cuya arquitectura de origen requiere una maquetación estática basada en coordenadas absolutas de pantalla, bloques binarios cerrados o páginas vectorizadas.

* **Fragmentación Silábica (`<span>` de coordenadas):** Al carecer de un flujo de prosa continuo, Calibre se ve obligado a reconstruir el texto calculando la posición espacial de las cadenas. La huella dactilar más destructiva es el troceado de palabras individuales en múltiples etiquetas `<span>` adyacentes, cada una inyectada con un estilo inline que determina su coordenada horizontal (`left`), vertical (`top` o `bottom`) o el espaciado entre letras (`word-spacing`).

* **Saltos de Línea Físicos (`<br>` residuales):** Para emular la visualización original del documento paginado, Calibre inserta elementos `<br class="calibre_pb_NN" />` o saltos de línea crudos al final de cada línea física de la maquetación original, impidiendo que el texto se adapte de forma fluida a pantallas con diferentes anchos de lectura.

* **Anulación de Semántica de Enlaces:** Las notas al pie en estos formatos de origen pierden por completo su condición de anotaciones marginales. Calibre suele convertirlas en bloques flotantes colocados aleatoriamente en el DOM debido a que su coordenada absoluta los sitúa "al final de la página visual", interrumpiendo párrafos a mitad de una frase.

#### Ejemplo de Estructura DOM resultante (AZW4/PDF a EPUB)

```html
<p class="calibre5">
  <span class="calibre_pos" style="left:120.5px;bottom:450.2px;word-spacing:12.3px;">Inge</span>
  <span class="calibre_pos" style="left:154.2px;bottom:450.2px;">nie</span>
  <span class="calibre_pos" style="left:178.1px;bottom:450.2px;">ría</span>
  <span class="calibre_pos" style="left:205.4px;bottom:450.2px;word-spacing:12.3px;"> Inversa</span>
  <br class="calibre_pb_4" />
  <span class="calibre_pos" style="left:120.5px;bottom:435.1px;">estructural.</span>
</p>

```

---

## 3. Linaje de Texto Primitivo o PDA

**Formatos incluidos:** `.pdb`, `.pml`, `.rb`, `.tcr`, `.snb`, `.txtz`.

### Análisis de Huellas Dactilares e Ingeniería Inversa

Este linaje proviene de formatos desarrollados para dispositivos móviles de primera generación (como Palm OS, Psion, Rocket eBook o cuadernos de notas elementales). Al no disponer de sistemas nativos de hiperenlaces complejos o hojas de estilo relacionales, Calibre procesa el texto plano de forma lineal.

* **Ausencia Completa de Hipervínculos:** Las notas al pie no están conectadas mediante elementos `<a>` en el DOM. Calibre vuelca la información de forma secuencial tal como aparece en el archivo plano de origen.

* **Notas al Pie como Texto Plano:** Las notas suelen ubicarse al final de cada "capítulo artificial" o al final de todo el libro, representadas como párrafos convencionales precedidos de un identificador visual estático entre corchetes, paréntesis o caracteres especiales (ej. `[1]`, `(Nota 1)` o `*1*`).

* **Huellas de Formateo Crudo:** Las llamadas a las notas dentro del cuerpo del texto se manifiestan simplemente como caracteres inline (ej. `"...de este modo [1] se procedió..."`), a menudo convertidos por Calibre en simples bloques tipográficos del tipo `<span class="calibre11">[1]</span>` sin ningún destino de navegación activo.

#### Ejemplo de Estructura DOM resultante (TXTZ/TCR/PDB a EPUB)

```html
<!-- Párrafo del cuerpo principal (Llamada ciega) -->
<p class="calibre4">
  La teoría de la relatividad especial fue formulada en 1905 [1] por Albert Einstein.
</p>

<!-- Bloque de notas acumulado al final del documento (Texto estático) -->
<p class="calibre15">REFERENCIAS:</p>
<p class="calibre16">[1] Publicado en la revista Annalen der Physik bajo el título "Zur Elektrodynamik bewegter Körper".</p>

```

---

## 4. Algoritmos Heurísticos de Detección y Limpieza (Python + BeautifulSoup + Regex)

La siguiente clase en Python, diseñada bajo principios de arquitectura de software desacoplada, expone los patrones de expresiones regulares y los métodos de navegación del DOM de `BeautifulSoup` óptimos para identificar cada uno de los tres linajes y normalizar sus estructuras destructivas.

```python
import re
from bs4 import BeautifulSoup, Tag, NavigableString

class CalibreEpubSanitizer:
    """
    Motor heurístico de ingeniería inversa para la limpieza de aberraciones
    estructurales inyectadas por el pipeline de conversión de Calibre.
    """
    
    def __init__(self, html_content: str):
        # Usamos lxml para mantener consistencia y velocidad de procesamiento del DOM
        self.soup = BeautifulSoup(html_content, 'lxml')
        
    def sanitize_fluid_lineage(self) -> None:
        """
        [LINAJE 1] Detecta y limpia el 'class soup' de calibreNN, normaliza IDs
        de notas y reconstruye hipervínculos bidireccionales accesibles.
        """
        # 1. Eliminar clases inútiles de calibre sin valor semántico (conservando estilos inline reales)
        calibre_class_pattern = re.compile(r'^calibre\d+$')
        for tag in self.soup.find_all(True, class_=calibre_class_pattern):
            # Filtrar para no destruir clases estructurales personalizadas
            classes = tag.get("class", [])
            cleaned_classes = [c for c in classes if not calibre_class_pattern.match(c)]
            if cleaned_classes:
                tag["class"] = cleaned_classes
            else:
                del tag["class"]

        # 2. Identificar y normalizar llamadas y destinos de notas al pie
        # Heurística de búsqueda: Enlaces con IDs o destinos que apuntan a 'note', 'footnote' o 'calibre_link'
        footnote_ref_pattern = re.compile(r'(calibre_link|note_id|footnote|fn_ref)-\d+|fn\d+')
        
        for anchor in self.soup.find_all('a'):
            href = anchor.get('href', '')
            anchor_id = anchor.get('id', '')
            
            if footnote_ref_pattern.search(href) or footnote_ref_pattern.search(anchor_id):
                # Asignar roles semánticos aria y epub para accesibilidad digital
                anchor['role'] = 'doc-noteref'
                anchor['epub:type'] = 'noteref'
                
                # Limpieza de caracteres de retroceso huérfanos inyectados por Calibre
                if anchor.string and anchor.string.strip() in ['←', '↩', 'back']:
                    anchor['class'] = 'backref'
                    anchor['role'] = 'doc-backlink'
                    anchor.string = '↩'

    def sanitize_fixed_layout_lineage(self) -> None:
        """
        [LINAJE 2] Resuelve la fragmentación de palabras uniendo etiquetas <span> contiguas 
        con posicionamiento absoluto inline, y elimina los saltos <br> físicos artificiales.
        """
        # 1. Consolidar spans fragmentados secuencialmente
        # Buscamos elementos contenedores (párrafos o divs) que albergan los spans de coordenadas
        for block in self.soup.find_all(['p', 'div']):
            spans = block.find_all('span', style=re.compile(r'(left|top|bottom|position\s*:\s*absolute)'))
            if not spans:
                continue
                
            # Agrupamos spans contiguos para fusionar sus textos si su distancia espacial es mínima
            current_span = None
            for span in list(spans):
                # Extraer la propiedad 'left' mediante una regex heurística para medir continuidad
                style_str = span.get('style', '')
                left_match = re.search(r'left\s*:\s*([\d\.]+)px', style_str)
                
                if left_match:
                    if current_span is None:
                        current_span = span
                    else:
                        # Si están contiguos en el DOM, fusionamos el texto
                        current_span.append(span.get_text())
                        span.decompose()  # Destruir span fragmentado redundante
                else:
                    current_span = None

            # 2. Limpieza de estilos de posicionamiento absoluto inline residuales
            for span in block.find_all('span'):
                style_str = span.get('style', '')
                # Reemplazar de forma segura atributos de coordenadas espaciales
                cleaned_style = re.sub(
                    r'(left|top|bottom|right|position|word-spacing)\s*:\s*[^;]+;?', 
                    '', 
                    style_str, 
                    flags=re.IGNORECASE
                ).strip()
                if cleaned_style:
                    span['style'] = cleaned_style
                else:
                    del span['style']

            # 3. Eliminar los saltos físicos <br> inyectados al final de cada línea de maquetación
            for br in block.find_all('br'):
                # Heurística: si el <br> está al final de un bloque o tiene clases de salto de página de Calibre
                if not br.next_sibling or (br.get('class') and 'calibre_pb' in ''.join(br.get('class'))):
                    br.decompose()

    def sanitize_primitive_text_lineage(self) -> None:
        """
        [LINAJE 3] Heurística para detectar notas estáticas no vinculadas (ej: "[1]") 
        en textos PDA/Primitivos, transformándolas en enlaces activos bidireccionales.
        """
        # Expresiones regulares para llamadas a notas inline: busca patrones tipo [1], [a] o (1)
        inline_ref_regex = re.compile(r'\[(\d+)\]')
        
        # 1. Localizar bloques de notas al final del documento (destinos)
        note_destinations = {}
        # Recorremos en orden inverso buscando párrafos que comiencen con el patrón "[1] Texto"
        for p in reversed(self.soup.find_all('p')):
            text = p.get_text().strip()
            match = re.match(r'^\[(\d+)\]\s*(.+)$', text)
            if match:
                note_num = match.group(1)
                note_text = match.group(2)
                
                # Crear un ID unívoco para el destino de la nota
                dest_id = f'fn_{note_num}'
                p['id'] = dest_id
                p['role'] = 'doc-footnote'
                
                # Envolver el contenido en una estructura semántica HTML5
                p.clear()
                num_span = self.soup.new_tag('strong')
                num_span.string = f'[{note_num}] '
                p.append(num_span)
                
                content_span = self.soup.new_tag('span')
                content_span.string = note_text
                p.append(content_span)
                
                note_destinations[note_num] = dest_id

        # 2. Reconstruir las llamadas de nota inline ciegas en el cuerpo de texto
        if not note_destinations:
            return  # No se detectó un almacén de notas estructurado de este tipo

        for element in self.soup.find_all(['p', 'span']):
            # Solo procesar elementos que contengan texto directo y no sean el propio destino de la nota
            if element.get('role') == 'doc-footnote' or not element.string:
                continue
                
            text = element.string
            matches = list(inline_ref_regex.finditer(text))
            if not matches:
                continue

            # Reconstrucción dinámica del nodo de texto inyectando los elementos <a>
            parent = element.parent
            current_index = 0
            new_contents = []

            for match in matches:
                note_num = match.group(1)
                if note_num in note_destinations:
                    # Texto previo a la llamada
                    new_contents.append(NavigableString(text[current_index:match.start()]))
                    
                    # Generar la llamada hipervinculada activa
                    call_id = f'fnref_{note_num}'
                    link_tag = self.soup.new_tag('a', attrs={
                        'id': call_id,
                        'href': f'#{note_destinations[note_num]}',
                        'role': 'doc-noteref',
                        'class': 'footnote-ref-reconstructed'
                    })
                    link_tag.string = f'[{note_num}]'
                    new_contents.append(link_tag)
                    
                    # Inyectar de paso el backlink de retorno en el párrafo de la nota destino
                    target_paragraph = self.soup.find(id=note_destinations[note_num])
                    if target_paragraph and not target_paragraph.find('a', class_='backref-reconstructed'):
                        backlink = self.soup.new_tag('a', attrs={
                            'href': f'#{call_id}',
                            'class': 'backref-reconstructed',
                            'role': 'doc-backlink'
                        })
                        backlink.string = ' ↩'
                        target_paragraph.append(backlink)
                        
                    current_index = match.end()

            # Añadir el texto remanente final
            new_contents.append(NavigableString(text[current_index:]))
            
            # Reemplazar el contenido del elemento original
            element.clear()
            for item in new_contents:
                element.append(item)

    def get_sanitized_xhtml(self) -> str:
        """Retorna el árbol de datos estructurado en formato XHTML limpio."""
        return self.soup.prettify()

```

---

## 5. Tabla Resumen de Diagnóstico Técnico

A continuación se presenta un mapa condensado de diagnóstico rápido para la identificación del linaje de conversión de Calibre según el formato de origen analizado:

| Familia de Linaje | Formatos de Origen Mapeados | Elemento Identificador Principal (DOM) | Complejidad de Limpieza | Riesgo Estructural Post-Conversión |
| --- | --- | --- | --- | --- |
| **Linaje Fluido/Hipervinculado** | `.mobi`, `.azw`, `.azw3`, `.lit`, `.htmlz`, `.fbz`, `.prc`, `.kepub`<br> | `class="calibreNN"`, `id="calibre_link-NN"` o similar

 | **Baja-Media**: Requiere aplanamiento de clases redundantes y accesibilidad ARIA.

 | Prácticamente nulo. El flujo de texto permanece reflowable y adaptable a pantallas modernas.

 |
| **Linaje de Maquetación Fija** | `.azw4`, `.chm`, `.lrf` (y PDFs nativos)

 | `<span style="left:...px; bottom:...px;">`<br> | **Alta**: Exige consolidación silábica mediante heurística espacial y purga de saltos `<br>`.

 | Muy alto. Palabras cortadas imposibilitan búsquedas de texto plano e indexación semántica.

 |
| **Linaje de Texto Primitivo** | `.pdb`, `.pml`, `.rb`, `.tcr`, `.snb`, `.txtz`<br> | Indicadores estáticos (ej. `[1]`) en párrafos de texto plano sin etiquetas `<a>` asociadas.

 | **Media**: Requiere parseo sintáctico mediante expresiones regulares para construir la red de enlaces.

 | Moderado. El texto es limpio y fluido, pero el lector pierde la navegación directa a las referencias de la obra.

 |
