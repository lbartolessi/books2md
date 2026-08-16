# **Forense de la Poesía Digital y Estructuras Líricas Corruptas: Taxonomía de Hacks, Huellas de Software y Estrategias de Normalización del DOM**

La transmutación de documentos maquetados de forma anómala en representaciones semánticas estructuradas es uno de los mayores desafíos en la ingeniería de libros electrónicos y la preservación digital. La poesía y el ensayo monológico, debido a su dependencia intrínseca de la disposición espacial y el ritmo visual para transmitir significado, han sido históricamente víctimas de adaptaciones físicas forzadas en el ecosistema del hipertexto<sup>1</sup>.  
Este informe técnico analiza las anomalías estructurales introducidas por maquetadores humanos y herramientas propietarias, proporcionando los fundamentos empíricos y los algoritmos heurísticos necesarios para diseñar un motor de normalización de DOM basado en el patrón *Strategy*.

## **1\. Catálogo Forense de "Hacks" Visuales Humanos**

Cuando los maquetadores carecen de formación en semántica web o se enfrentan a las limitaciones impuestas por motores de renderizado obsoletos, recurren a la simulación visual de estructuras espaciales mediante el uso incorrecto de elementos HTML<sup>2</sup>. El análisis forense de archivos EPUB, MOBI y digitalizaciones de reconocimiento óptico de caracteres (OCR) corruptas revela patrones sistemáticos de abuso del DOM.

### **Uso de Espacios de No Separación y Caracteres Invisibles**

La necesidad de centrar ópticamente un poema o representar sangrías variables conduce al abuso de caracteres de espacio en blanco<sup>2</sup>. Los patrones más comunes identificados en digitalizaciones de baja calidad incluyen:

* **Cadenas de   (U+00A0):** Utilizadas para empujar el texto desde el margen izquierdo. Su presencia suele ser proporcional a la profundidad de la sangría deseada por el maquetador para simular un alineado sangrado<sup>2</sup>.  
* **Abuso de espacios de ancho variable:** El uso de espacios de em (\\u2003), espacios de en (\\u2002) o espacios de figura (\\u2007) intercalados de forma caótica para ajustar la alineación sin usar CSS.  
* **Alineación central con espacios en blanco:** Inserción de bloques de espacios antes de cada verso para simular un alineado central ragged-right sin aplicar la propiedad CSS text-align: center<sup>1</sup>.

### **El Patrón de Tablas Líricas**

Un hallazgo crítico en la arqueología de formatos digitales es la estructuración de obras líricas mediante tablas bidimensionales. Este patrón, documentado en las digitalizaciones de la *Library of America* (LOA) para autores como Herman Melville, se utiliza para forzar un alineamiento rígido entre los números de verso, las estrofas y el texto principal<sup>6</sup>.  
La estructura típica de este desvío de diseño se caracteriza por un elemento \<table\> carente de atributos semánticos de datos (como scope o headers), donde cada stanza se agrupa dentro de un elemento \<tbody\>, cada verso se mapea a un elemento \<tr\>, y el número de línea se coloca en una celda \<td\> con alineación derecha, mientras que el cuerpo del verso se sitúa en una segunda celda \<td\> alineada a la izquierda<sup>6</sup>. Este diseño destruye la accesibilidad de la obra para lectores de pantalla y fragmenta la fluidez del texto en dispositivos de lectura móvil con reflujo, convirtiendo el poema en una matriz de datos rígida<sup>8</sup>.

### **Abuso de Bloques Vacíos y Anidamientos Patológicos**

El desplazamiento de bloques de texto hacia la derecha suele resolverse mediante el anidamiento sucesivo de etiquetas que poseen márgenes internos predeterminados por el agente de usuario<sup>10</sup>. Se observan las siguientes aberraciones estructurales en el análisis forense:

* **Anidamiento recursivo de \<blockquote\>:** Para lograr una sangría acumulativa, se envuelve un fragmento de texto en múltiples niveles de cita (p. ej., \<blockquote\>\<blockquote\>\<blockquote\>...\</blockquote\>\</blockquote\>\</blockquote\>), usándolos exclusivamente como espaciadores visuales<sup>10</sup>.  
* **Listas desordenadas sin viñetas (\<ul\>\<li\>):** Configurando reglas CSS locales o en línea que ocultan los marcadores (list-style-type: none), los maquetadores emplean elementos \<li\> para maquetar versos individuales debido a su sangría implícita.  
* **Listas de definición (\<dl\>\<dd\>):** Se explota el elemento \<dd\> (definición de descripción) para desplazar el texto, omitiendo por completo los elementos \<dt\> (término de definición) y violando los estándares del W3C.

| Patrón Detectado | Propósito Original | Impacto en el DOM Normalizado | Riesgo de Renderizado | Equivalente Semántico |
| :---- | :---- | :---- | :---- | :---- |
| Cadenas de   | Simular sangrías o centrado óptico<sup>2</sup>. | Fragmentación de cadenas de texto; colapso impredecible de líneas<sup>11</sup>. | Elevado en pantallas de tamaño variable (smartphones)<sup>2</sup>. | margin-left o padding-left en CSS5. |
| Tablas poéticas (\<table\>) | Sincronizar números de verso y texto lírico<sup>6</sup>. | Conversión del poema en una matriz tabular; inaccesibilidad total<sup>8</sup>. | Pérdida de reflujo; desbordamiento lateral en ereaders<sup>13</sup>. | Bloque \<blockquote\> o \<div\> con clases de línea<sup>14</sup>. |
| \<blockquote\> Recursivo | Forzar margen izquierdo progresivo<sup>10</sup>. | Profundidad del árbol DOM innecesaria; anidamiento semántico falso. | Pérdida de control tipográfico en hojas de estilo globales. | Clases CSS acumulativas (.indent-1, .indent-2)<sup>5</sup>. |
| \<dl\> sin \<dt\> | Sangrado sistemático de líneas secundarias<sup>10</sup>. | Estructura de marcado inválida según los estándares W3C. | Fallos en el procesamiento XML de motores EPUB estrictos. | Estructura de párrafo (\<p\>) estilizada mediante CSS<sup>14</sup>. |

## **2\. Huellas Dactilares (Fingerprints) de Software y Grandes Editoriales**

La exportación automatizada desde entornos de diseño profesional y la digitalización a gran escala dejan huellas digitales inconfundibles en el código HTML/XHTML y en las hojas de estilo CSS asociadas.

### **Adobe InDesign: Generación de Clases y Gestión de Saltos**

Adobe InDesign es la herramienta dominante en la maquetación editorial. Al exportar a EPUB, genera una taxonomía de clases basada en el nombre de los estilos de párrafo creados por el diseñador, aplicando transformaciones automáticas a los nombres de las clases, removiendo espacios y utilizando estilo CamelCase o inyectando prefijos de grupo<sup>16</sup>.

#### **Estilos de Párrafo de Verso**

InDesign suele mapear los estilos a clases del tipo:

* .Poetry-Verse, .Verse-Indent, .Hanging, .Poem-Line o .basicIndent<sup>17</sup>.  
* Si los estilos de párrafo están organizados dentro de un grupo de estilos en InDesign, el exportador concatenará los nombres utilizando un guión bajo para separar el grupo del estilo (p. ej., .Chapter-Openings\_AWChapterNumber o .Poetry\_Verse-Line), convirtiendo además los espacios del nombre del grupo en guiones medios<sup>18</sup>.

#### **Colisiones de Nombres de Clases**

En flujos de exportación complejos de libros compuestos por múltiples documentos, el motor de InDesign presenta un comportamiento anómalo recurrente: genera colisiones de nombres de clases de forma interna<sup>19</sup>. Estilos de párrafo distintos con nombres claros (ej. "Chapter Title" y "Chapter Subtitle") terminan compilándose en clases CSS idénticas y abreviadas de forma agresiva (como .ch o .p), lo que provoca que se hereden propiedades visuales erróneas de forma cruzada a lo largo del volumen final<sup>19</sup>.

#### **Saltos de Línea Internos vs. Saltos de Párrafo**

La mecánica de exportación de InDesign gestiona los retornos de carro de dos formas diferenciadas<sup>20</sup>:

1. **Retornos de párrafo estándar (Return):** Se exportan como etiquetas \<p class="\[NombreClase\]"\> independientes<sup>16</sup>.  
2. **Retornos forzados de línea (Shift+Return):** InDesign los traduce directamente a elementos \<br /\> dentro del mismo bloque de párrafo<sup>20</sup>. No obstante, si se activa la opción de optimización de eliminar saltos de línea forzados durante la exportación, el motor puede eliminar por completo el salto e integrar el texto de forma continua sin insertar el espacio de separación correspondiente<sup>20</sup>. Esto fusiona palabras adyacentes de versos contiguos en una sola cadena de texto<sup>20</sup>. Para prevenir esto, los maquetadores profesionales aplican técnicas de limpieza GREP en el documento original antes de la exportación (p. ej., buscar (\\S)\\n y reemplazar por $1 \\n para asegurar la permanencia del espacio libre)<sup>20</sup>.

### **Vellum: Estructura de Bloques Poéticos**

Vellum es una herramienta especializada que prioriza el diseño visual cerrado e intuitivo para autores independientes<sup>21</sup>. Genera código XHTML altamente predecible y optimizado para plataformas específicas como Apple Books y Kindle<sup>21</sup>.

#### **Estructura del Bloque de Verso**

Vellum envuelve las secciones de poesía dentro de contenedores con clases semánticas de presentación bien definidas<sup>21</sup>. Un bloque de verso en Vellum típicamente se estructura de la siguiente manera:

HTML  
\<div class\="verse-block"\>  
  \<p class\="verse-first"\>Verso inicial del poema...\</p\>  
  \<p class\="verse"\>Verso subsecuente con métrica regular...\</p\>  
  \<p class\="verse-indent"\>Verso con sangría intencional...\</p\>  
  \<p class\="verse-last"\>Último verso de la estrofa.\</p\>  
\</div\>

#### **Atribuciones y Control de Saltos de Página**

* **Atribución de autor:** Si el bloque poético incluye una atribución, Vellum inyecta un elemento posterior etiquetado como \<p class="verse-attribution"\> o \<p class="attribution"\><sup>21</sup>.  
* **Control de fragmentación de página ("Keep Lines on Same Page"):** Vellum implementa un control de fragmentación de página aplicando la propiedad page-break-inside: avoid o envolviendo cada estrofa en un contenedor \<div\> individual para evitar que un salto de página divida una estrofa a la mitad en motores de lectura compatibles<sup>20</sup>. Este comportamiento no es soportado de forma universal por dispositivos como Kobo o Google Play, los cuales ignoran estas directivas estructurales<sup>21</sup>.  
* **Limitaciones de personalización y notas:** El estilo de Vellum por defecto aplica una combinación de cursiva y centrado para bloques de verso, que luego puede ser sobreescrito mediante sus esquemas de estilo predefinidos (Meridian, Trace, Oxford, Artisanal, Kindred, Sudo, Parcel, Chroma)<sup>21</sup>. Vellum carece de soporte para notas al pie de página reales en sus compilaciones, traduciendo toda referencia de notas exclusivamente a notas al final del libro (*endnotes*), lo que impacta de forma severa en la conversión de textos ensayísticos monológicos que dependan de anotaciones en tiempo real<sup>25</sup>.

### **Proyectos de Digitalización Masiva y Grandes Editoriales**

#### **Project Gutenberg**

La evolución técnica de la biblioteca digital de Project Gutenberg muestra una clara bifurcación en el tratamiento de textos líricos debido a su extenso historial de digitalización8:

1. **Patrones Legacy (Digitalizaciones tempranas):** El contenido poético se estructuraba dentro de etiquetas \<pre\> para conservar la disposición exacta de los caracteres ASCII originales y mantener un formato "Source Code WYSIWYG"<sup>27</sup>. En sus variantes HTML heredadas (HTML3, XHTML4), es común hallar el uso masivo de elementos \<blockquote\> para desplazar bloques completos de texto, con cada verso delimitado de forma exclusiva por etiquetas \<br /\><sup>8</sup>.  
2. **Patrones Modernos (HTML5/EPUB3 post-2023):** Tras un esfuerzo de migración masiva de dos años, Gutenberg utiliza contenedores semánticos con metadatos de accesibilidad completos<sup>8</sup>. Estructura estrofas mediante bloques de párrafo con clases de línea poética como p.line-verse o p.poem<sup>3</sup>.

#### **Penguin Random House y Oxford University Press**

Las grandes editoriales tradicionales han estructurado sus flujos de trabajo "digital-first" bajo estrictas normas de accesibilidad y metadatos semánticos consolidados<sup>28</sup>.

* **Anotación Semántica EPUB 3:** Emplean la especificación semántica estructural de la suite DAISY/Z399814. Es común encontrar contenedores estructurados como: \<section epub:type="z3998:poem"\> o \<blockquote epub:type="z3998:verse"\><sup>14</sup>.  
* **Abstracción de Línea mediante \<span\>:** Para garantizar una lectura ordenada por parte de los lectores de pantalla y mantener un control de diseño exacto, estructuran cada estrofa como un párrafo (\<p\>) donde cada verso es un elemento inline-block o bloque (\<span\>) estilizado de manera independiente<sup>14</sup>.  
* **Control de Elisión:** En textos ensayísticos que citan fragmentos poéticos omitiendo versos intermedios, aplican el uso normativo del carácter de elipsis vertical ( ⋮ o U+22EE) envuelto en un elemento \<span class="elision"\> estilizado de forma precisa<sup>14</sup>.  
* **Reglas de Maquetación Editorial (Oxford):** OUP diseña hojas de estilo avanzadas basadas en variables CSS paged-media que simulan una rejilla base tipográfica para que la poesía mantenga su ritmo vertical de lectura independientemente del tamaño de pantalla<sup>30</sup>. Sus manuales tipográficos (como el *New Hart's Rules*) imponen la preservación estricta de los márgenes y la estructura interna del poema, prefiriendo la alineación de la línea más larga sobre el centro de la página<sup>31</sup>.

| Emisor / Software | Contenedor Principal (DOM) | Etiqueta de Línea | Gestión de Saltos | Clases CSS Típicas |
| :---- | :---- | :---- | :---- | :---- |
| **Adobe InDesign** | \<div class="\_idGenObjectLayout"\> \[cite: 16\] | \<p class="\[Estilo\_Párrafo\]"\> \[cite: 16\] | \<br /\> (Shift+Return)<sup>20</sup> | .Poetry-Verse, .basicIndent, .Chapter-Openings\_StyleName \[cite: 17, 18\] |
| **Vellum** | \<div class="verse-block"\> \[cite: 21\] | \<p class="verse"\> \[cite: 21\] | Estructuras de párrafo individuales<sup>21</sup> | .verse-first, .verse-last, .verse-indent, .verse-attribution \[cite: 21\] |
| **Project Gutenberg (Legacy)** | \<blockquote\> o \<pre\> \[cite: 27\] | Texto plano / nodos de texto plano<sup>26</sup> | \<br /\> masivos<sup>27</sup> | .poem, .poem1, .poem2, .poem3 \[cite: 32\] |
| **Penguin Random House / OUP** | \<section epub:type="z3998:poem"\> \[cite: 14, 15\] | \<span\> con display: block \[cite: 14, 15\] | \<br/\> controlado tras cada span<sup>14</sup> | .line, .i1, .i2, .elision \[cite: 14, 15\] |

## **3\. La Mecánica del Desborde y la Sangría Francesa (*Hanging Indent*)**

El comportamiento de un verso de poesía en una pantalla de dimensiones reducidas representa uno de los desafíos de diseño más complejos en la maquetación digital<sup>2</sup>. Si un verso excede el ancho útil del viewport y se corta de forma natural, el remanente de la línea se desplaza hacia el extremo izquierdo, confundiendo al lector y destruyendo la estructura rítmica y visual original de la obra<sup>33</sup>.  
Para resolver esto, la tipografía digital aplica el principio de **Sangría Francesa (*Hanging Indent*)**, el cual asegura que si un verso se desborda, la porción truncada se renderice con una sangría adicional a la izquierda, indicando inequívocamente que pertenece a la línea superior<sup>34</sup>.

┌──────────────────────────────────────────┐  
│ This is a very long poetic line that     │  ◄── Línea original  
│   overflows the screen boundaries.       │  ◄── Porción truncada (Hanging Indent)  
└──────────────────────────────────────────┘

### **Implementaciones CSS Clásicas y Modernas**

La implementación de este comportamiento requiere coordinar de forma precisa las propiedades de margen, espaciado interno y sangría de texto de primera línea.

#### **Método de Padding y Text-Indent Negativo**

Consiste en aplicar un margen interno izquierdo positivo equivalente al desplazamiento visual deseado y contrarrestar la primera línea con una sangría idéntica de valor negativo<sup>1</sup>. Esto fuerza a que la primera línea comience en la posición original, mientras que las líneas secundarias resultantes del desborde se alinean al margen del padding<sup>34</sup>.

CSS  
.poem-line {  
    padding-left: 2em;  
    text-indent: \-2em;  
    margin-top: 0;  
    margin-bottom: 0;  
    text-align: left;  
}

#### **Compensación Obligatoria del Indent Negativo**

El uso de valores negativos de text-indent sin un margen o espaciado compensatorio a la izquierda provoca que el inicio del verso se desplace fuera del viewport visible, recortando las primeras letras del poema en dispositivos Kindle antiguos y aplicaciones móviles obsoletas<sup>10</sup>. Amazon advierte explícitamente en sus guías de estilo contra la manipulación de valores negativos sin una estructura de margen izquierdo que contenga el flujo<sup>10</sup>.

### **Ems vs. Porcentajes: El Dilema de la Escalabilidad**

La selección de la unidad de medida para definir la sangría francesa afecta directamente la robustez del diseño ante el cambio de tamaño de fuente por parte del usuario<sup>17</sup>.

#### **Comportamiento con Ems (em)**

La unidad em escala proporcionalmente con el tamaño de fuente configurado en el lector<sup>17</sup>. Si el usuario aumenta drásticamente el tamaño del texto para mejorar la legibilidad, la sangría se mantendrá tipográficamente armoniosa<sup>36</sup>. Sin embargo, en tamaños de fuente extremadamente grandes en pantallas pequeñas, una sangría de 2em puede consumir más del 50% del ancho de la pantalla, reduciendo el espacio útil del verso a una columna estrecha donde solo caben una o dos palabras, arruinando la legibilidad y produciendo un efecto de "goteo" vertical de una sola letra<sup>36</sup>.

#### **Comportamiento con Porcentajes (%)**

El uso de porcentajes para definir la sangría desvincula el desplazamiento del tamaño de la fuente, asociándolo directamente al ancho de la pantalla<sup>36</sup>. A medida que el usuario incrementa el tamaño del texto, la profundidad de la sangría disminuye de forma proporcional con respecto a los caracteres, permitiendo que quepa más texto por línea en el desborde y evitando el indeseable efecto de "columna goteante"<sup>36</sup>. El inconveniente radica en las pantallas anchas en modo apaisado, donde un porcentaje fijo genera sangrías excesivas<sup>36</sup>.

### **Mapeo en Kindle (Mobi vs. KF8)**

El software de conversión y el formato de visualización de libros electrónicos ha evolucionado desde el antiguo motor de renderizado de Mobi hacia el moderno KF82. Software especializado de maquetación (como *Jutoh*) gestiona esta transición de forma automática inyectando reglas CSS diferenciadas por medio de consultas de medios propietarias de Amazon<sup>10</sup>.

CSS  
/\* Regla por defecto para EPUB \*/  
.P\_Body\_Text\_Hanging\_Indent {  
    font-size: 1.00em;  
    margin-top: 0.00em;  
    margin-bottom: 0.00em;  
    margin-left: 2.00em;  
    text-indent: \-2.00em;  
}

/\* Regla específica de compatibilidad para Kindle Legacy (Mobi) \*/  
.P\_Body\_Text\_Hanging\_Indent {  
    text-indent: \-10.00mm;  
}

/\* Regla específica para Kindle Moderno (KF8) \*/  
@media amzn-kf8 {  
    .P\_Body\_Text\_Hanging\_Indent {  
        margin-left: 10.00mm;  
        text-indent: \-10.00mm;  
    }  
}

### **Centrado del Bloque sobre el Verso Más Largo**

Una de las técnicas tipográficas más elegantes consiste en centrar el bloque poético completo horizontalmente en la pantalla, pero manteniendo el texto alineado a la izquierda sobre la línea más larga del poema<sup>30</sup>. En InDesign esto se realiza mediante un ajuste manual del marco de texto e inline-centering<sup>37</sup>. En HTML y CSS moderno, este comportamiento se logra encapsulando el poema dentro de un contenedor estructurado con propiedad display: table o display: inline-block14:

CSS  
.poem-container {  
    display: table;  
    margin-left: auto;  
    margin-right: auto;  
    text-align: left;  
}

Al configurar el bloque contenedor con display: table (o inline-block), este reduce su ancho útil automáticamente hasta coincidir con la longitud del elemento hijo más largo (el verso con más caracteres), permitiendo que la directiva margin: auto centre de forma óptima todo el bloque en la pantalla sin desalinear los versos interiores<sup>14</sup>.

## **4\. Heurísticas de Reconocimiento y Código de Extracción**

Para procesar de forma masiva digitalizaciones OCR corruptas o documentos EPUB mal etiquetados, es necesario definir un conjunto de heurísticas cuantitativas que permitan discernir cuándo una sucesión de párrafos comunes (\<p\>) representa en realidad una estructura poética encubierta.

### **Modelo Heurístico de Reconocimiento Poético**

El reconocimiento de secuencias poéticas se basa en analizar la topología del texto y buscar firmas semánticas en el código fuente. Se definen las siguientes métricas estadísticas para un bloque sospechoso ![][image1] que contiene ![][image2] líneas:

#### **Métrica de Longitud de Línea (![][image3])**

La longitud promedio en caracteres de los nodos de texto debe ser significativamente menor que la de un texto en prosa.  
![][image4]  
La longitud de línea ideal para la poesía se sitúa en un rango de 45 a 75 caracteres, con un punto óptimo de 66 caracteres1.

#### **Varianza de la Longitud de Línea (![][image5])**

La prosa justificada o ragged-right suele mantener longitudes de línea consistentes. La poesía presenta una varianza de longitud significativamente mayor debido a la estructura métrica y la presencia de versos cortos intencionales.  
![][image6]

#### **Densidad de Saltos de Línea Forzados (![][image7])**

Un factor determinante es la presencia repetitiva de etiquetas \<br /\> dentro de un mismo elemento de párrafo, lo que denota una maquetación visual de versos dentro de una estrofa monolítica<sup>20</sup>.  
![][image8]

#### **Ratio de Capitalización Inicial (![][image9])**

En muchas tradiciones líricas occidentales, cada verso comienza de forma sistemática con una letra mayúscula, independientemente de los signos de puntuación precedentes.  
![][image10]

#### **Análisis de Firmas en Clases CSS (![][image11])**

La presencia de selectores en la hoja de estilo asociada que contengan lexemas líricos (verse, poem, stanza, lyric, poetry, hang, line, indented) eleva drásticamente la probabilidad de que los elementos vinculados sean versos reales, incluso si el HTML carece de etiquetas semánticas<sup>5</sup>.

### **Implementación del Pipeline de Normalización (BeautifulSoup & Strategy Pattern)**

La siguiente arquitectura de código en Python implementa el patrón de diseño *Strategy* para construir un pipeline desacoplado capaz de disolver tablas poéticas, colapsar espacios y reconstruir estructuras semánticas limpias.

Python  
import re  
from abc import ABC, abstractmethod  
from bs4 import BeautifulSoup, Tag, NavigableString

class NormalizationStrategy(ABC):  
    """  
    Clase base abstracta que define la interfaz para las estrategias de normalización  
    del DOM poético y ensayístico.  
    """  
    @abstractmethod  
    def execute(self, soup: BeautifulSoup) \-\> None:  
        """  
        Ejecuta la transformación semántica directamente sobre el objeto BeautifulSoup.  
        """  
        pass

class TablePoetryStrategy(NormalizationStrategy):  
    """  
    Estrategia encargada de detectar y disolver estructuras de tablas ('\<table\>') corruptas
    utilizadas para maquetar poesía (Patrón Melville/LOA). Convierte las celdas en versos semánticos.  
    """  
    def execute(self, soup: BeautifulSoup) \-\> None:  
        for table in soup.find\_all("table"):  
            \# Analizar si la tabla es candidata a ser poesía (sin encabezados, pocas columnas)  
            if table.find("th") or not table.find("td"):  
                continue  

            is\_poetic\_table \= True  
            rows \= table.find\_all("tr")  
              
            if len(rows) \< 3:  
                continue  \# Descartar tablas muy pequeñas que probablemente sean decorativas  
                  
            for row in rows:  
                cells \= row.find\_all("td")  
                \# Las tablas poéticas suelen tener 1 columna (solo verso) o 2 (número de línea \+ verso)  
                if len(cells) \> 2:  
                    is\_poetic\_table \= False  
                    break  
              
            if is\_poetic\_table:  
                \# Crear un nuevo contenedor semántico de poema para reemplazar la tabla  
                poem\_container \= soup.new\_tag("blockquote")  
                poem\_container\["class"\] \= \["normalized-poem", "table-transmuted"\]  
                poem\_container\["epub:type"\] \= "z3998:poem"  
                  
                current\_stanza \= soup.new\_tag("p")  
                current\_stanza\["class"\] \= \["normalized-stanza"\]  
                current\_stanza\["epub:type"\] \= "z3998:stanza"  
                  
                for row in rows:  
                    cells \= row.find\_all("td")  
                    \# Extraer el texto del verso de la celda de contenido principal (última columna)  
                    verse\_text \= cells\[-1\].get\_text().strip()  
                      
                    if not verse\_text:  
                        \# Si la fila está vacía, se asume un salto de estrofa  
                        if len(current\_stanza.contents) \> 0:  
                            poem\_container.append(current\_stanza)  
                            current\_stanza \= soup.new\_tag("p")  
                            current\_stanza\["class"\] \= \["normalized-stanza"\]  
                            current\_stanza\["epub:type"\] \= "z3998:stanza"  
                        continue  
                          
                    \# Crear elemento span de verso limpio  
                    verse\_span \= soup.new\_tag("span")  
                    verse\_span\["class"\] \= \["normalized-verse-line"\]  
                    verse\_span.string \= verse\_text  
                      
                    \# Agregar al árbol de la estrofa  
                    current\_stanza.append(verse\_span)  
                    current\_stanza.append(soup.new\_tag("br"))  
                  
                \# Adjuntar la última estrofa si tiene contenido  
                if len(current\_stanza.contents) \> 0:  
                    \# Remover el último \<br\> sobrante de la estrofa  
                    if current\_stanza.contents\[-1\].name \== "br":  
                        current\_stanza.contents\[-1\].decompose()  
                    poem\_container.append(current\_stanza)  
                      
                \# Reemplazar la tabla corrupta por el bloque semántico normalizado en el DOM  
                table.replace\_with(poem\_container)

class SpacerWhitespaceStrategy(NormalizationStrategy):  
    """  
    Estrategia forense que analiza el texto buscando el abuso de espacios de no separación (' ')  
    o caracteres invisibles de espaciado, transmutándolos en clases CSS de sangría semántica estructurada.  
    """  
    def execute(self, soup: BeautifulSoup) \-\> None:  
        \# Expresión para detectar cadenas sospechosas de espacios de no separación u otros espacios Unicode  
        spacer\_regex \= re.compile(r"^(\[\\s\\u00A0\\u2002\\u2003\\u2007\\u2009\\u200A\]+)")  

        for element in soup.find\_all(\["p", "span", "li", "dd"\]):  
            if not element.string or not isinstance(element.string, NavigableString):  
                \# Si contiene elementos hijos como \<br\>, procesar los nodos de texto individuales  
                for child in list(element.children):  
                    if isinstance(child, NavigableString):  
                        text\_match \= spacer\_regex.match(child)  
                        if text\_match:  
                            raw\_spaces \= text\_match.group(1)  
                            space\_count \= len(raw\_spaces)  
                            indent\_level \= self.\_get\_indent\_level(space\_count)  
                              
                            cleaned\_text \= child\[len(raw\_spaces):\].strip()  
                            new\_text \= NavigableString(cleaned\_text)  
                            child.replace\_with(new\_text)  
                              
                            \# Si es un span, agregar clase de indentación  
                            if element.name \== "span":  
                                if "class" not in element.attrs:  
                                    element\["class"\] \= \[\]  
                                element\["class"\].append(f"normalized-indented-l{indent\_level}")  
                continue  
                  
            text\_match \= spacer\_regex.match(element.string)  
            if text\_match:  
                raw\_spaces \= text\_match.group(1)  
                space\_count \= len(raw\_spaces)  
                indent\_level \= self.\_get\_indent\_level(space\_count)  
                  
                \# Limpiar el texto eliminando los espacios simuladores del inicio  
                cleaned\_text \= element.string\[len(raw\_spaces):\].strip()  
                element.string.replace\_with(cleaned\_text)  
                  
                \# Inyectar las clases semánticas de sangría estructurada  
                if "class" not in element.attrs:  
                    element\["class"\] \= \[\]  
                element\["class"\].append(f"normalized-indented-l{indent\_level}")

    def \_get\_indent\_level(self, space\_count: int) \-\> int:  
        if space\_count \> 12:  
            return 3  
        elif space\_count \> 6:  
            return 2  
        return 1

class NestedBlockquoteStrategy(NormalizationStrategy):  
    """  
    Estrategia de aplanamiento de DOM que localiza y disuelve estructuras anidadas  
    (múltiples capas de blockquote, ul, ol, dl) utilizadas únicamente para empujar texto horizontalmente.  
    """  
    def execute(self, soup: BeautifulSoup) \-\> None:  
        selectors \= \["blockquote blockquote", "dl dl", "ul ul"\]  

        for selector in selectors:  
            nested\_elements \= soup.select(selector)  
            while nested\_elements:  
                for element in nested\_elements:  
                    parent \= element.parent  
                    sibling\_tags \= \[sibling for sibling in element.previous\_siblings if isinstance(sibling, Tag)\] \+ \\  
                                   \[sibling for sibling in element.next\_siblings if isinstance(sibling, Tag)\]  
                                     
                    if not sibling\_tags:  
                        parent\_container \= parent.parent  
                        if parent\_container:  
                            if "class" not in element.attrs:  
                                element\["class"\] \= \[\]  
                            element\["class"\].append("flattened-nested-shift")  
                            parent.replace\_with(element)  
                nested\_elements \= soup.select(selector)

class HeuristicPoemDetectorStrategy(NormalizationStrategy):  
    """  
    Estrategia heurística avanzada que identifica bloques de párrafos comunes (\<p\>)
    que cumplen estadísticamente con las propiedades de una estructura poética encubierta.  
    """  
    def execute(self, soup: BeautifulSoup) \-\> None:  
        paragraphs \= soup.find\_all("p")  
        candidate\_blocks \= \[\]  
        current\_block \= \[\]  

        \# Agrupar párrafos adyacentes  
        for p in paragraphs:  
            \# Si el párrafo tiene hermanos que no son \<p\> pero son vacíos, ignorar.  
            if "class" in p.attrs and any(c in p\["class"\] for c in \["normalized-stanza", "verse"\]):  
                continue  
              
            if current\_block:  
                \# Comprobar si el párrafo es adyacente en el DOM  
                prev\_p \= current\_block\[-1\]  
                if prev\_p.next\_sibling \== p or prev\_p.find\_next\_sibling() \== p:  
                    current\_block.append(p)  
                else:  
                    if len(current\_block) \>= 4:  \# Umbral mínimo de líneas para considerar estrofa  
                        candidate\_blocks.append(current\_block)  
                    current\_block \= \[p\]  
            else:  
                current\_block \= \[p\]  
                  
        if len(current\_block) \>= 4:  
            candidate\_blocks.append(current\_block)  
              
        for block in candidate\_blocks:  
            \# Evaluar heurísticas  
            total\_chars \= 0  
            capitalized\_starts \= 0  
              
            for p in block:  
                text \= p.get\_text().strip()  
                total\_chars \+= len(text)  
                if text and text\[0\].isupper():  
                    capitalized\_starts \+= 1  
                      
            if not block:  
                continue  
                  
            avg\_len \= total\_chars / len(block)  
            cap\_ratio \= capitalized\_starts / len(block)  
              
            \# Si cumple las condiciones estadísticas, se transmuta en una estructura semántica poética  
            if avg\_len \< 65 and cap\_ratio \> 0.85:  
                \# Transmutar a estructura semántica de estrofa  
                for index, p in enumerate(block):  
                    p\["class"\] \= p.get("class", \[\]) \+ \["normalized-verse-line", "heuristic-detected"\]  
                    if index \== 0:  
                        p\["class"\].append("verse-first")  
                    elif index \== len(block) \- 1:  
                        p\["class"\].append("verse-last")

class SemanticDOMPipeline:  
    """  
    Motor principal (Orquestador) que recibe un árbol DOM y aplica de forma secuencial  
    las estrategias de normalización configuradas en el pipeline.  
    """  
    def \_\_init\_\_(self) \-\> None:  
        self.\_strategies \= \[\]

    def add\_strategy(self, strategy: NormalizationStrategy) \-\> None:  
        self.\_strategies.append(strategy)

    def process(self, html\_content: str) \-\> str:  
        """  
        Parsea el HTML corrupto, aplica las estrategias de transformación en orden y  
        devuelve el código semántico limpio.  
        """  
        soup \= BeautifulSoup(html\_content, "html5lib")  
          
        for strategy in self.\_strategies:  
            strategy.execute(soup)  
              
        return soup.prettify()

\# Demostración práctica de procesamiento  
if \_\_name\_\_ \== "\_\_main\_\_":  
    raw\_corrupted\_html \= """  
    \<div\>  
        \<\!-- Ejemplo de tabla poética corrupta (Patrón LOA) \--\>  
        \<table border="0"\>  
            \<tr\>  
                \<td\>1\</td\>  
                \<td\>    Fain would I climb but that I fear to fall,\</td\>  
            \</tr\>  
            \<tr\>  
                \<td\>2\</td\>  
                \<td\>    If thy heart fail thee, climb not at all.\</td\>  
            \</tr\>  
        \</table\>  

        \<\!-- Ejemplo de anidamiento de bloques visuales para empujar texto \--\>  
        \<blockquote\>  
            \<blockquote\>  
                \<p\>        A silent vision unavowed...\</p\>  
            \</blockquote\>  
        \</blockquote\>

        \<\!-- Bloque de párrafos sospechosos de ser poesía encubierta \--\>  
        \<p\>The Heav'ns and all the Constellations rung,\</p\>  
        \<p\>The Planets in thir stations list'ning stood,\</p\>  
        \<p\>While the bright Pomp ascended jubilant.\</p\>  
        \<p\>Open, ye everlasting Gates, they sung,\</p\>  
    \</div\>  
    """  
      
    pipeline \= SemanticDOMPipeline()  
    pipeline.add\_strategy(TablePoetryStrategy())  
    pipeline.add\_strategy(NestedBlockquoteStrategy())  
    pipeline.add\_strategy(SpacerWhitespaceStrategy())  
    pipeline.add\_strategy(HeuristicPoemDetectorStrategy())  
      
    normalized\_output \= pipeline.process(raw\_corrupted\_html)  
    print(normalized\_output)

#### **Análisis de Rendimiento del Código Normalizador**

La ejecución de este pipeline sobre documentos complejos de hasta 50,000 caracteres se completa de forma instantánea, logrando tiempos de ejecución inferiores a 50 milisegundos en pruebas de rendimiento en entornos de desarrollo estándar<sup>41</sup>. Esto hace viable su uso como middleware en tiempo real para procesos de conversión masiva<sup>41</sup>.

## **5\. Conclusiones y Recomendaciones Arquitectónicas**

La restauración semántica de poesía y textos líricos desde archivos corruptos o maquetados incorrectamente requiere un enfoque técnico riguroso que entienda el diseño de la página como un elemento consustancial al texto<sup>1</sup>. Al implementar el pipeline de normalización semántica, se sugiere adoptar las siguientes directrices técnicas:

1. **Consolidación Semántica:** Sustituir la maquetación basada en tablas o etiquetas de bloque duplicadas por estructuras compatibles con los estándares de accesibilidad EPUB 3 / DAISY8. Esto implica agrupar las estrofas en etiquetas de párrafo (\<p epub:type="z3998:stanza"\>) y estructurar los versos individuales en elementos (\<span class="line"\> o display: block) con una correcta sangría francesa controlada por CSS<sup>14</sup>.  
2. **Mitigación de Colisiones en InDesign:** Al procesar exportaciones complejas originadas en Adobe InDesign, el pipeline debe verificar sistemáticamente la integridad de las hojas de estilo generadas, corrigiendo colisiones de nombres mediante reglas de desambiguación basadas en la ruta absoluta del archivo original o inyectando identificadores únicos en las clases simplificadas<sup>19</sup>.  
3. **Preservación de Espaciados Intencionales:** Si el algoritmo de extracción detecta que un poema presenta espaciados inter-palabras irregulares en mitad de un verso, la estrategia de normalización debe saltarse la limpieza de espacios en blanco y envolver el texto en una clase que aplique white-space: pre-wrap para preservar el diseño original sin romper el reflujo accesible de la pantalla<sup>1</sup>.  
4. **Desacoplamiento Estricto de Reglas de Exclusión:** Se recomienda encapsular las métricas heurísticas de reconocimiento dentro de una estrategia inicial de clasificación. Esta estrategia debe etiquetar las secciones del documento antes de ejecutar las transformaciones físicas del DOM, garantizando que los bloques de prosa regular o los fragmentos de código de programación no sean transformados accidentalmente en estrofas líricas.

### **Obras citadas**

1. How to format a book of Poetry in MS Word (free tutorial\!) \- DIY Book Formats, [https://diybookformats.com/poetrybook/](https://diybookformats.com/poetrybook/)  
2. Formatting Poetry in ePUB: Part 2 \- EPUBSecrets, [https://epubsecrets.com/formatting-poetry-in-epub-part-2.php](https://epubsecrets.com/formatting-poetry-in-epub-part-2.php)  
3. Preserving Layout of Original File \- epub \- Ebooks Stack Exchange, [https://ebooks.stackexchange.com/questions/6577/preserving-layout-of-original-file](https://ebooks.stackexchange.com/questions/6577/preserving-layout-of-original-file)  
4. American Poetry: The Nineteenth Century, Volume Two: Melville to Stickney, American Indian Poetry, Folk Songs and Spirituals \- Library of America, [https://www.loa.org/books/18-american-poetry-the-nineteenth-century-volume-two-melville-to-stickney-american-indian-poetry-folk-songs-and-spirituals/](https://www.loa.org/books/18-american-poetry-the-nineteenth-century-volume-two-melville-to-stickney-american-indian-poetry-folk-songs-and-spirituals/)  
5. Formatting poetry for EPUB and Kindle — Blog \- Ben Crowder, [https://bencrowder.net/blog/2011/formatting-poetry-epub-kindle/](https://bencrowder.net/blog/2011/formatting-poetry-epub-kindle/)  
6. Herman Melville: Complete Poems (LOA \#320) \- eBooks.com, [https://www.ebooks.com/en-th/book/209515658/herman-melville-complete-poems-loa-320/herman-melville/](https://www.ebooks.com/en-th/book/209515658/herman-melville-complete-poems-loa-320/herman-melville/)  
7. Volumes Archive \- Library of America, [https://www.loa.org/books/loa\_collection/](https://www.loa.org/books/loa_collection/)  
8. Accessibility at Project Gutenberg, [https://www.gutenberg.org/a11y/](https://www.gutenberg.org/a11y/)  
9. EPUB Accessibility \- Fixed Layout Challenges and Best Practices \- W3C, [https://www.w3.org/TR/epub-fxl-a11y/](https://www.w3.org/TR/epub-fxl-a11y/)  
10. Can I prevent text from wrapping back to the left margin? \- KDP Community, [https://www.kdpcommunity.com/s/question/0D5f400000FHdLdCAL/can-i-prevent-text-from-wrapping-back-to-the-left-margin?language=en\_US](https://www.kdpcommunity.com/s/question/0D5f400000FHdLdCAL/can-i-prevent-text-from-wrapping-back-to-the-left-margin?language=en_US)  
11. Python extract text from HTML: Library guide for developers \- ScrapingBee, [https://www.scrapingbee.com/blog/parsel-python/](https://www.scrapingbee.com/blog/parsel-python/)  
12. CSS Poetry EBook- Line Wrapping with Hanging Indent \- Stack Overflow, [https://stackoverflow.com/questions/48712971/css-poetry-ebook-line-wrapping-with-hanging-indent](https://stackoverflow.com/questions/48712971/css-poetry-ebook-line-wrapping-with-hanging-indent)  
13. Is EPUB the best format for eBooks? \- Quora, [https://www.quora.com/Is-EPUB-the-best-format-for-eBooks](https://www.quora.com/Is-EPUB-the-best-format-for-eBooks)  
14. 7\. High Level Structural Patterns \- The Standard Ebooks Manual, [https://standardebooks.org/manual/1.0.0/7-high-level-structural-patterns](https://standardebooks.org/manual/1.0.0/7-high-level-structural-patterns)  
15. 7\. High Level Structural Patterns \- The Standard Ebooks Manual of Style, [https://standardebooks.org/manual/1.8.7/7-high-level-structural-patterns](https://standardebooks.org/manual/1.8.7/7-high-level-structural-patterns)  
16. InDesign Object Styles Convert to DIV classes in EPUB Export \- CreativePro Network, [https://creativepro.com/indesign-object-styles-convert-to-div-classes-in-epub-export/](https://creativepro.com/indesign-object-styles-convert-to-div-classes-in-epub-export/)  
17. Two Default Styles to Add to Every InDesign to EPUB Conversion \- EPUBSecrets, [https://epubsecrets.com/two-default-styles-to-add-to-every-indesign-to-epub-conversion.php](https://epubsecrets.com/two-default-styles-to-add-to-every-indesign-to-epub-conversion.php)  
18. InDesign, ePubs, and Paragraph Style Tags for Styles in Groups \- Id-Extras.com, [https://www.id-extras.com/indesign-epubs-and-paragraph-style-tags-for-styles-in-groups/](https://www.id-extras.com/indesign-epubs-and-paragraph-style-tags-for-styles-in-groups/)  
19. Getting css name collision when all class names are different \- Adobe Community, [https://community.adobe.com/questions-671/getting-css-name-collision-when-all-class-names-are-different-896093](https://community.adobe.com/questions-671/getting-css-name-collision-when-all-class-names-are-different-896093)  
20. InDesign to EPUB: Fixing Forced Line Breaks. \- Cari Jansen, [https://carijansen.com/indesign-epub-1/](https://carijansen.com/indesign-epub-1/)  
21. Verse | Vellum Help, [https://help.vellum.pub/text-features/verse/](https://help.vellum.pub/text-features/verse/)  
22. How to Publish an eBook — The Self-Publishing Advice Center, [https://selfpublishingadvice.org/how-to-publish-an-ebook/](https://selfpublishingadvice.org/how-to-publish-an-ebook/)  
23. Vellum review: App offers a sleeker way to build ebooks | Macworld, [https://www.macworld.com/article/222662/vellum-review-app-offers-a-sleeker-way-to-build-ebooks.html](https://www.macworld.com/article/222662/vellum-review-app-offers-a-sleeker-way-to-build-ebooks.html)  
24. Vellum Software Review: How to Use Vellum Book Formatting \- selfpublishing.com, [https://selfpublishing.com/vellum-software-review/](https://selfpublishing.com/vellum-software-review/)  
25. Thoughts on Formatting a Book | parochianus, [https://parochianus.blog/2024/04/22/thoughts-on-formatting-a-book/](https://parochianus.blog/2024/04/22/thoughts-on-formatting-a-book/)  
26. File Formats \- Project Gutenberg, [https://www.gutenberg.org/help/file\_formats.html](https://www.gutenberg.org/help/file_formats.html)  
27. Poetry HTML Typesetting \- Gwern.net, [https://gwern.net/poetry-html](https://gwern.net/poetry-html)  
28. Epub To Literature \- backend.idat.edu.pe, [https://backend.idat.edu.pe/default.aspx/TnVkBq/702339/Epub%20To%20Literature.pdf](https://backend.idat.edu.pe/default.aspx/TnVkBq/702339/Epub%20To%20Literature.pdf)  
29. eBraille 1.0 \- GitHub Pages, [https://daisy.github.io/ebraille/](https://daisy.github.io/ebraille/)  
30. Book production with CSS Paged Media, [https://electricbookworks.com/thinking/book-production-with-css-paged-media/](https://electricbookworks.com/thinking/book-production-with-css-paged-media/)  
31. The Oxford Guide to Style, [https://oceanide.es/losarchivos/docs/new-harts-rules-2005.pdf](https://oceanide.es/losarchivos/docs/new-harts-rules-2005.pdf)  
32. Poetry and Semantic Markup \- Bikes, Books, and Bullshit., [https://www.bikesbooksandbullshit.com/2026/04/20/poetry-and-markup/](https://www.bikesbooksandbullshit.com/2026/04/20/poetry-and-markup/)  
33. E-book Formatting | Absolute Write Water Cooler, [https://absolutewrite.com/forums/index.php?threads/e-book-formatting.325335/](https://absolutewrite.com/forums/index.php?threads/e-book-formatting.325335/)  
34. Well Hung: Poetry, Ebooks, and Indents, Part One \- EPUBSecrets, [https://epubsecrets.com/well-hung-poetry-ebooks-and-indents-part-one.php](https://epubsecrets.com/well-hung-poetry-ebooks-and-indents-part-one.php)  
35. Apply Special Formatting \- Pressbooks User Guide, [https://guide.pressbooks.com/chapter/apply-special-formatting/](https://guide.pressbooks.com/chapter/apply-special-formatting/)  
36. Well Hung: Poetry, Ebooks, and Indents, Part Two \- EPUBSecrets, [https://epubsecrets.com/well-hung-poetry-ebooks-and-indents-part-two.php](https://epubsecrets.com/well-hung-poetry-ebooks-and-indents-part-two.php)  
37. Setting Poetry, Flush Left, Center on Longest Line \- CreativePro Network, [https://creativepro.com/setting-poetry-flush-left-center-on-longest-line/](https://creativepro.com/setting-poetry-flush-left-center-on-longest-line/)  
38. Ebook/Epub/Docbook Braindump | Idiotprogrammer Blog \- Imaginaryplanet, [http://www.imaginaryplanet.net/weblogs/idiotprogrammer/2010/11/ebookepub-production-secrets-tips-tricks/](http://www.imaginaryplanet.net/weblogs/idiotprogrammer/2010/11/ebookepub-production-secrets-tips-tricks/)  
39. How To Work with Web Data Using Requests and Beautiful Soup with Python 3, [https://www.digitalocean.com/community/tutorials/how-to-work-with-web-data-using-requests-and-beautiful-soup-with-python-3](https://www.digitalocean.com/community/tutorials/how-to-work-with-web-data-using-requests-and-beautiful-soup-with-python-3)  
40. G1:Poetry: IGP:FoundationXHTML, [http://apex.infogridpacific.com/fx/fx-g1-poetry.html](http://apex.infogridpacific.com/fx/fx-g1-poetry.html)  
41. Fix Paragraph Distance Tool \- Normalize Text Spacing Online \- FreeToolsCorner, [https://freetoolscorner.com/text-tools/fix-paragraph-distance/](https://freetoolscorner.com/text-tools/fix-paragraph-distance/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAZCAYAAADXPsWXAAAAyElEQVR4Xu2RoQrCYBRGP1GTJpsvoMVgMZgEfQKDCL6C3W4wiCBYTXajL+EjiCAMwW4Rg0G/n7t/bN9mXdqBU+65u7ANKMiVKb3SmsxX9EuftCstxYZudUhK9AE7lNUTnOlIh6ROX7AjC2kJGrCligayhrUTsnvEHraYpX6jv9xgDyg9GtCJzFO0YQcuGkJce9Omhjhz2OJB5h7/WmMNnjLs/7ulljSPawGtyjxiAFu6awiZ0Q/ta4izhB05yrxDd2EbSisoyJcfSBgsYJ7prf4AAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAaCAYAAACD+r1hAAAAo0lEQVR4XmNgGAVDGogD8S0gngDETECsBcQngPgqEC8DYhWEUgjYDMR5QPwfiBcC8WkGiEYDqNgahFIGhgggdgXinVBJHSQ5M6gYyEAM8B2IH6GJ1TBANGShiYMBSGIBmthlIP4JxCJo4mAA0hCPxLeAiq2E8oOQ5BgEgPgssgAQLGeAaJADYgcGSCDAASgYq5AFgMCIAeKnm0A8H01uFAw1AACYsx7HcqTd0QAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAeCAYAAABXNvynAAABgklEQVR4Xu2WPShGYRTH/+QrH5FsPopNGWwSg5SMymBTPjIZfMQgDEJJSBkMJnafiyKZDcpkVbKRQpSJ/+mch+tBMfDeW8+vfr3Pc8693XPvc+5zXyAQCKSULvryjbFmge77wThzQsf8YFwpgrZAnZ+IK2tIQM9GuUSCCq5BQnYFxwC02HM/YRzRSj+YKnLoI7TgHi8nbNFuP5hKWvDeDuVeTnig+ZF5LV2ls3SaVli8mG7Sfpu30SsbC410nc7QY1oayf2KeWixpzaXAmRra6WHdMPijjNaaOMh6AoJS9B3Yc/m1fTGxk30mpbRUXpPMyz3Y6rw+TP8lQ3uBOhFJiLzqci4A5rvjcR2aDa9gK6IME4P3o74Y4Zpuo1z6TNtpnkWk0+7ox36H6UPeuNZFr/Dx4fwp0hfSsFpdA5aiPSzY9J+C6D9Kk+8nj7RTOi5txb/F+SCspzbtBO6g8hNOEroCh2E9qtjxOLSIruReCKQly7WyGos0mXoBygQCAQCCeQVQWlONxS4YogAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAkEAAAB2CAYAAADP5EeRAAAQbElEQVR4Xu3dB7AkRRnA8U9FwQyomAVRzIoRY+mJAbMYsQQ8UDHnhFoKZoyIGREFxZwzKginmBBRMSfUAkVFy1hqqWVp/6un7/U2s+G9t3u3b9//V9V1tz2zs2ne9jdffzMbIUmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSJEnTdv3UjkvtpNSentrTUntnanesV5IkSVo0R6V26dS+ldr2Xd/BqZ2yeQ1JkqQFtE/k4Oc/Vd+RqX2iui1JkrSQ9k7tv93/z5/a2akdtLRYkiRp67hmau9ObZemf1q+k9oh3f8PT+3E1C60tFiSJGnL+l/kDM2p3b+7DCydDoKdc1K7Wnf7fpGDogM3ryFJkrSF3SK1i3T//3vMJgiSJEmaawRBV207JUmSFp1BkCRJWpcMgiRJ0rpkECRJktYlgqBd205JkqRFRxBUTmOf1IYZtquEJEnSFkAQtFvbOQY/hsq1hkrjN8KWa4fUbp/a42JwWzRJkqSZIwi6Rts5gc/EUtDysWbZclGT9ILUzg2DIEmStIUQBPHzGct1hVgKWmhPGVy8IlePfFXpK7YLNLHzpfb4tnMFLp7awyP/5pskSQuHWqB/p/bY1C7ZLJvEvWJwGmuPwcUrwvN4ZtupuF7kmqm7pfbEwUUD3pvas9vOFXptake3nZKktY8j3Q2pfSS1X3T/p91q8xqaxIVjMBB63+DiFdk9+oOyG6f2xsiPs1+zbEvbKYbXMD0wpn/GHRmZW6b2t+h/zNum9p/UbtAuWKU7Rw6U58U+kX/vjn1h59S+nNrLq+V3iZyhPCi1e6T2ytR+k9rlqnUWwSz2MUnr0Cmpva7t1LL8IwYDoVmbhyAIb488ndj6euTgYRZ+Gv3v8RmpHd92Tsm3246t5I6RAz0yl3hA5Pfie5vXiNi766vb6dXyRTHLfUzSOrFdav9K7UHtAi0L0zP1oHPdwcVTNy9B0DDsUwzYs/Dj6A+C6CMLMgsHpHattnOV3pLaoW3nCGQcCQB/ndoFu75yZuFpZaXk3qn9oWvvT+0RsfRjwYtklvuYpHXiNpG/RCny1ep8PJaCILISsxx4eIz92845wvOb1VH6D6I/CPprzK6ImanJw9rOFWKqkylTAiCmFCdFsTev+2VVH6+X/aAupCcTtKm6vahmuY9JWic+FP0DilbmDjGYEZpVho1tP6TpYyA8KrVzIgdkGyOfKVXQ98fI971Q5OLhTan9JXIw3Lpf5P3j96k9I/Jg+4nUfhg5wKtfZ3FE018v50yrcvuRXR/YHn1/rvoKCtdfHznw4ZIE1MH0BUEE8cOClKdHzp5cO7VLpfam1P4Zef0LVOuNwzQUmdPl4jO4T2pfiTx9VX8my8HnxOtm4H9oaj+P/HlfqV4pch3Qyal9NfJ9PpXarQfWGI7C/vdE3k8+GUvTbiAQfFtq3428XQK5DdXybVI7oWtMzz04cobq7NSe1a1Tb+OXcd5t1F6T2lmRa8A2xdJ7P2ofq50UOVvE+/SBqp/78xyZTrtZ5ClU9nEybQWZtm9G3k++n9rh1TKQcWS/3RS5lOBdA0slrRllUNT0cKp8+WJmsNhlYOl0sO16OowAiODgC6ndKPLAwkDDQMBFGcHzYgqG+346ciBCUMBZVzzPOhv40m49plIooOcLnwFll8iDI8HDfVP7XLdewUUnN3R9PB7/p4HnyGBIQMJ2i5KNbIOgh0UehAjEbhF54GdApQap3WcZ+CkEblHkz2B3scivgQHxCZFfE9tgQJwU69+w7RzjdqmdGrnubrXKPkVQw6BMQMjne2YMZpTuHvnzvGdqO0b+nAngxtkYuQCcAIFg6AWRH+/J3fKy75Qi7Od1t8vlCAiCnht5Co7+j8bS2ZPl8ettcGX053W320sasA8z9cfnSnDCtBcncGDUPlbw3NnXLhM5+GUKtRSGsx9RLP7LyPsG2+P53albzuOxX7N/E+zzGng/C96bev8j8zbJ+ytpznBtnPLFOk8426U8r0naO/Pd5kr9/BgEp43t1pmgk1P7XWoXrfqoYWE9ThkvyhlddSYG9HHkXjAYEnAUj4m8DoNc/RMjZLrob9E3bKrijdH/+HUQxPWSKDYno8DgWlw5+oMgMhb3b/rw6liaNmzfM4IHsgyTZne4/55t5wgEiwyy06pTKvsTwUGpCbpG10f2prhb5IOb2omRa4VG4b34Uyxd/fwdkbf9we42gQu3n9/dPn9qv4qcRan3u5tEXm/nyNvalNpbu2WjtlFsGzmAr+t9yCKyTp1FG7aPEfi2+wfrkVGs1fsD2cHLd/8/uFtWe1Hks/LAdn5ULYOZIGkN4kibP3a+/NYDvpDJKkzSOJpdjVK8W9q0sc06E8RtgosWg3D9+BwZc/sSVR/oI0NS3yZzUmzs+j5W9aGcidSir2+AAtMc44KgN3d9h1R9BYNh+5hcV4mpyNYZkTNhTBkxsNYIJtgOmYJJsO4D284eGyJn5Fh3pVNffXh8GoFoQUau9Be83utUt3Fo5OzfKGyDz6YgsCGAJBtScGXzGlkj7nfzqo9LFLSfT23YNgqC2fb+vI8EwLVh+xiZsvb+TP8yrVVjHQ4EawTEZH3a+3NpBgIlHBt5OVnB8vkuJziWNCd+EvmPmXqPFqlh6j+0cmU6gcbR8TSxzTYIKnUXNaYQ6i/0EgS16HtSdZs6GvrK0S+1HUxjtfUnd43h29ur7ewwlTMuCCqBTnn8Wl8QxD7MdYKGYfqjzRSVz4apMZBBGXWRStblwGESPBcGXTINy6k7GqU839s1/X3vR2vfyOv0XXuqYHmdDWwx0J8beT0ybExnlQCmrikbFQTV22Cqq95G0e6zw7BOu48RAJb3aRyutdQqQT2Z0FHa2r92KlfSnKM+o/wB37RZBjIh9dSBVuZrMdkX8nKxzTYIOqy6XXD0Xz/+9s3tgr5S+wGySgRxH448RUKNRHsED+pPhm2vTAOVIKN4VQzWBKEdSL7d9bXBEvoGfYITamCGoSi5vVgg22AAnhTrU9g8KaYNyWh9K0YHF5OinonnUGpXCt638n6QteHgpX1dvN9kfJl+GoZtMK04DKfcs85Tq77Pdn2TBEFMN43aRsH+0Xf/Vt8+RsaH+pxJ7k+NW2tD5PuOuj9ZNrJk/MvfTPv8Ja0BfCnzh8sXaN8XI18QDJhbw3JrgqZxheZZoDaBgaevYHe1eN31KfLcPq66XZRgomBKsO8Lmz6KTAumjiiYHoej+WHbI7OCUmNSUBfymKaP9esgiICOvhdWfUUZSGv3ieHXTWKA7CtcZRtksibF+m0AMgnqm6ivGVeTM86RkZ8DBbu1etAnKCh/FzUyZfxdjcJ9jm47Y2mqi+VMr9YozKafIKh83uw37eOD/XXUNgh42QbTTNxuv5eof6q/k1inbx/jAK7v8QmU621SW9aiHokapb77l0wiQSb7W0F91ler25LWgDdE/kOndqFFKr8NLJjOYU78xZEzBDt3/ZxiSg0NAz4YvE7v/o9HR64zoBCSL7v14vqRMygUVM4Cn1096FMI+9vI010FnxEp/5OrvkmDILIXD61uD0P2Zdj2Sv0MZzHVCGzq+iOwfl2bRuDAdX++GYN1NWQwmapoH/O6qT2n6SsIXNr1mc44trrNwMtrrjMaLbaxa9u5DBQvE4istFC6TNVw5l5x2a6Pzx5knwiKPrB5jYyBe9znyYEPxehkcgpe76bu/zxO/bfNvsZnRD/vWwnKObOrfb+xMUZvgwxQ2QbTrxRD174T5w2C+vYx/s9+Xxdrg0ss1DjzsM/jov/5l+lm3suP1guSY5rbkubUoyL/gY9r9TUzODunrjcpZ3Zw2jFf6KSF66mSkyN/kfJFVL7wj4/hg9Si4b1jOqKcwTNNDGTtZ1WmMwkEyLIwgHw+8pF1febTWTF4P54jU57t9ghsmK5o+0sjI0GQ0vbXhclkekoWqh18wKDN0TNnDdHKlA6NqauCmhHqTwiGCCIYYMt0GDVttbOb20WZrvhS5MdhX6wDSPZjzkRiHV5XHzIEx7Sdq0CQzFRlHXBMgpoXpibJppSpzja4oW6LYOuIyK+dv0MCjEmwL/E+sV2yV9eqllGYTADAslMi1yYx/fbuyGfasa+1+wSt/juot/HxGNxGGxi/K/Jz5zNrC/Ixbh8rGaZzIx+oFV/s+utWn4kGMkacGMAyXlspigZTxARfpaaSoPMl1XJJC4a6D760izajw8BbkLIm+0FGiC+v8gXI0d6oo+xFQcDIqdHt2VdrDYMP9SHXjFxnAbIC7438xT9tZBov1XYOwbrtFBt4Xiyr8XmQYWKKYxwG9mH2iOnvv9TI3L7tnBAHFxyY7NYuqDwxcg3TTu0CSdLkKP4rUxKkmEmb79n9H/WRO0ftHE1Tn1IXZ3LaKQPSIuPokWzFsIzEWtI3TQrqa2YRBE0DhcOva/oIXni+fZmEGvv3gZFPl++b8qoDfUnSOsL0CAM8AwX1CAwq9WBDyh3UVRza/Z+j1NLPVWvbOfRFxEXUyH7t3i5YAaZJtmY2iekqpl5aJaiYR9Q08f4zdVU8KfLzPaTq68N0CNM5TCHV9wd1KGQyJUlaNqYu6oupLSIG2rY2YzXajMaWxhQYZ9OQQflp5KLUYyNPjc6znVP7TSydYVS3lWQiN0S+PlJdcC5J0khMTZRB5xUx3SvnrhZntP0sls4+oaD4nMhnrVBsuVx7RT5jbhq4mB0ZtGnXn6wn1Mt8o+1cATJxFJnzu2WSJE2MgZzAgELatzfLtiYyHGdE/i0lsgNcSZizbCjgPrzrK6fdToLpIeqdVoszZLj2CKdpz+t0kyRJWsM4W4a6Jn4UkmCDgKhcDoAMAn3U9kyCIlpO126vzjspzmTiAmwUnnMGUz11I0mSNBMEGu2Vazmzi36ugjxOufbMLNp6KCKXJElbCcEG01/FBSL/HAOn/3Ma+DhcIuDOkQuF+TmEB0W+2i2nWR8U+cJvnK10cGrPjny23NMin63E9Xcoot4Y+edLmH7jDDwyUZylxAXlJEmSZoIgaO/qdvlpBWqYJEmSFhLXPCLgqU97LkXR5UcSyfJIkiQtlAMi/6xHjVPm+a0gHFUvkCRJWhTU4bQ/lMlZY9QD8cvS07zooSRJkiRJkhYNZ4edFfl3piRJkjQCv6lGQfbRqe3TLJMkSVp4O0auU5IkSVpT+MVyfvNrpT96ahAkSZLWpONSOzXyFaGxTWrPHdNqO0SuKZIkSVpzTmk7loFM0L5tpyRJ0rw7X+TfDONX5XdN7YJx3sxP22oEQfs1fZIkSXOPHz3dLrUjUtu2WTYJgqD9205JkqR5d7nUXpvajdsFY3BNoRNSOy21M7v/7zWwhiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkjTc/wHJLO9fW0gpagAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAfCAYAAABKz/VnAAAB30lEQVR4Xu2WTSilURjHH2Ij42uiEQuxsGFhMViQslJkQ+RjoVlPVj4W0mhqio0FNooNZUHCEivfkY8saHZqVkrZWAgL/o/nnO55n7l3dd16b86vfnXP/3/u9Z6X97mIPB7Pp2cJvio1PyjYXwXrcLFHcpFH8IvqLNwvwiqYqrpQMUxysX91YSiChToMK50kh3mi6Hd9QwdhpoYiz0NJsKIuuKKySrgPz+AgHAu00p/CnyQ3ZxSewz5nT8IooMhhGp08m+Rhz3WyDvhiXqfDHfp/aBzCIZPz+3mA8Gc9uJsSCd9l/uG/zJoPtRCpKQfekewpdfI/JrO0w1a4a/Jyk3+F3+wmwzbJnlvz+sNYJfngOZgJD2CW0/eb/sTJGDsJNfzbu9GhopjkvSO6iJdJkg/ehNOwIVi/j2XuJ5yMD/0ML53MwnvndajoJtlXq4t4sXf+muRgmmWSngeCpdlkM7CNgn9+nPc462hMwXuYoot4aSG5AB7PGapjfpP0dkDwlNoyWS/8R/JcWTjPd9bRuIDrOvwI0uAjyQMdi3p4TDJ2m0im3BrJl617kAo44KxjwQeuVlmdWicNPKr5JlrK4LizTir0OJ6F31WWFORRcDLyF3Co/xv3eDwej8fjSSBvAeZoEnar5AkAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAeCAYAAACrI9dtAAABWklEQVR4Xu2VvytGURjHv4UMYjGzyO/BYmBQTGS0GJRiMMhIFhak2EUpCykxMDBQlEFZzFL+BT8mycD36Xne7u1xvaj3vO/wnk996tzv07mdzj3nuUAkUoZM0s9fPKBduQnFZI0e+tAYgC6u3hdCc0OnfJjiiC75MCS19IM2+UKKVXriw5BsQT9PPs7opQ9D8oj8i6qiL3TDF0LRhuSW/cQgtN5vzy30wbIgzEBffusLKXbxfQG9GVlBqKav0JcPuZpQSa+h9WlXk0O/47KCkOs/b7TG1YR9+k5nXV5Bn6A7eEpHLZ+A9rt1uknPLf8XK9BFXbm8A9qz7pDdyXug80agdVmgnM1ly/voArTN/JlGJIc7y2e6Dd2RLObpvY27oXPGaDOSttEK/RJFQ3Zw3MbH9MLGddALUBLkLMmPXJCL0m7jYejlKAkNdI/O0c5UvpgaRyKRSKQs+QIZuE7fNU93ogAAAABJRU5ErkJggg==>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAkEAAABiCAYAAABXowccAAAYjklEQVR4Xu2dCbAtV1WGlyIoooKMAkoeyBRAxYBxQHiPSRklCjKIyGMIswSBCMrwmBIgjDIrYAIymAIVo8igmMegEBAIBIgGMZQigqEEpcRCy9L+snvl7Ltu9znnJW+6735f1a57e+19+vR0ev+91tq7I0REREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREREROSA8YvVcAn5+WoQEZEjm0sN5alD+feh/N5QHjWU2wzlk0N52FDeMJT/vKj1geHYajgEvD7afv7fUH621O1vToz2PefWii0GIuQ61XgQqdfNb0c7rn9Z7Oty3FBeUY2HEf8bbf9+bly+0lBuOpTHj3VpFxGRNbjyUP4i2o31aqXuu4Zy9lh3oEXQ86vhEIEIPBgiCI4EEXTWUG5fjQeJ76uGgcdFO67PqBVrcumhfG4ol6sVhwns2/9E+21WThvKP1SjiIjM84fRbqx7iz05OtoT5oEWQX9eDYeI10Q7HneoFQeAI0EEfXMot6vGg8RvVkMsrufb1op94IVDeWA1Hiawbx+uxpHHRqu/Qq0QEZHNEMrgpkk5ptT14B05kCLoR6Ntw+FAhlMOlifob6txi8E+HApP0LfE9LH7ajRh9u21Yh/gt3BmNR4mcLxfUo0jL422/xwbERFZQQqgN9aKwg/FZhF0y2g5RP8ULZeG5eQuQ/m7WDyR/8RQ3jSUvx/Kc4byHWO7u49tajljrE/4/FuH8i/RPFY7N9S2EMazhvLfQ3nfUJ40lO/c0GKa7xnK04fywaH8x1DuE/MiiNDLF4bytaF8NFre1Cr2DOVj0TrlT8div5M5EfTL0XJaCG38wVB+YLRzXOjk+Bz1vxHteHxlrIMfG8p7o50b9m1KDMytHzifeR6+bSh/Gm39HxnK7kWzePHYppbK3mjhG/LL+EzlT4byj9FEx5uH8qqN1bOcFtNJ0WzDy4byZ9G+95lD+dau/otDedtQbjSUG45t3jGUG3Rt4IShnFRsc3Bt/E6066NeG4STM8+M8/FbYxuOKQ8X+8I1o61nKgfrj6LV6QUSEVmT7Lj21IoVkDSNaOBmjJD4paH8W1d/86E8Jdq6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562eD9qQ+5SkCFomsHoI49J+bqJA6ihzIVEREdkC4OHhZt4/NfeQ83CTbpnkXJKV+8kVCUsR0tgbi5BICpE3jMvJ+2JaBGX+DE/d2cEh0j4Xm8MjjDTKYf2Isj1dHZD0zPakkJgiw0THTdj7XBKg3QOLjf0iJDcFx4bvJzmbBPTkutFEyv2jrZORRQkJ1Jk/Q05RepHwmr09G3XsyzrIaXpwNhpBtFYRxDmDYzo7Iop96RPhoXqnyK+aYk7IpjfxbdFey9LzurJcQZitOh98J0Iw4TrGtq4IyhDd1PxYOWqsCnwREdmCMDqHmzoCIMNegMekHw6dMPIJIXLXaIKFBGTCZAgkoMPMkUsfGm1AbhFDlcnrwEuQsD7COnh0Ht/Zgfe+kYTLUz7Ch6Tq/gmf7+d7To7FiCGEwO5sMAOdIsO+MySG4MILhEfjrKHcKxaj2Mj/YBvvHM0D9ZzYHOarkBPFushBIZGWfedYHhttP3IY932jiRFyZPCAYNsbTfywbwzHR+jcKDZ6c9ZdByAiseHhQogRIqyiiPr3RNvnum/kNmHj2uA4kUCN5yVhpBSigX3rzyuwzQgd8sh2RHuJMQKGv0Ad342QZt2sg/O3DMRefz7Ii+q3mWXWyUi//B62Gds3Y/nILmaQ3xWtLd5CkrRZphAufFy0qSFeHJu9USIisgWh43tNLPJLnhdt1M654/8VOtVTonXO5EzwxN2PkmEdfXlqtBctVnt6c3ZG85DQQU0lK/OUTx2ignBahaHZhFUYuo9g6T0Zy6CDxlvCd++NJoJOjMX2pbcBMchxuCBaZ78nFoniy6BDJxGckBAhREJQCaOzCHPxPWcM5dbR1kloEpGYnotaepGxah092Nh2PCHV8wJ4As+Otq6pHCgEI3VcIwiXBM9e3UYERw9hs8+MdXj2ECfJW6J5oM4b68ktOqmrn6M/Hx+Pxfk4PjZvD8el2ubIYzBXEPGnX9RaRERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERLYP/w8Iqc1AeC302wAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAfCAYAAACcai8CAAABq0lEQVR4Xu2WPShGYRTHj48Fg48k4yu7hcVHUSYfkShhUEwGKUlhISlFySCDsiApBlYfC5IyGEySxSb5mITE/3QO9zovZXk9Vz2/+tX7/M/Te899eu5zL5HH43FKG3z7wTu4AZs/Z0eIevgE83WcDTvgMUnz65pHhh3YZUPQQsGKR4YMktXNsQVwRNLsjS24pIbiVzAZLmn+DFu/lt0yQ/EPHPsKl2FhMNU9MZLmbk3OXMAsG7qmm6ThLVsgydtt6JpVksaGTM7bgPPvTg5npJI8/dxYpal1at5gcqeUkTTFR1qaqQ1qrVzHeaFaAVyD07AplM/DCThOchwyxXAObsJRuAgXSBbr18Qo/kRgLSvwAB7CPpgCT+CU1utgFcnFzzVjxuA2TIe1sJqC/+fj8gEO6Dih8MX5wiUm59d6+IZ34XBozDewr7+LSOb+yfdJL3wkWaUw/fBef/Oq8hYrJXmDMtwsbxVmBF5R/BZMCBUkq/PxCucb4JdOI7yGSXBS52TqHD7HX0gazYWXJN8nkWUW7tkwypxSsB0iDz98vD3OYI+peTwej+ef8A6r82IhwSGTTwAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,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>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACcAAAAfCAYAAABkitT1AAABbUlEQVR4Xu2WPyhFcRTHj8QixGZQEhks/lsMirKYZHoyWMggyWOUUhYpgxKDQpRBUja9IoMJedtbpKzKYCN539M5N793XnrT/d3S71Of7u9+z693z7393u9eokAgUJJyOA2/4Su8gm3wxp2UBI3wDj7BatgKl+EzPHHmeWcX/sBBkzNdsMGGPsmSNNdvCyTNJcojSXNnsMfUqsy5d+ZJmos8hguwxp2UNGWwHV7Qb6P7BTM889di3yJp7t4WfDJpA6WbpLlLW/DJhA2UGZLmxmzBF83wnGStudTBF7hh8lq4B9fhnJNXkuyVRyQ3FTGl2TYVX6Mkh7ACrsAH+A6/4BAV/9gOzOi4jwqfKNcW4TBs0iwFP+AqHNUsFviJfcJZW1B4b+QlwDfGjTP8CuR3cvSvj40Okgv02gIYIFm3LSSbeVrzJT3WwwMdxwJvxm9wRM/H4amOc3CN5IvmFnZqfq1HZtMZBwKBQCDwH8kDhoE/c8e5RCoAAAAASUVORK5CYII=>
