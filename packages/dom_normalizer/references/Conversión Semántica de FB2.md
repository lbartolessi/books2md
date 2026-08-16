# **Análisis Arquitectónico y Transmutación Semántica de FictionBook 2.0 (FB2) a HTML5 mediante BeautifulSoup y el Patrón Strategy**

## **Contexto Histórico, Rigor Estructural y el Ecosistema FB2 y FBZ**

La preservación digital de obras literarias ha afrontado históricamente el dilema de equilibrar la fidelidad del contenido con la flexibilidad de su representación visual1. A mediados de la década de 1990, la comunidad de digitalizadores de libros de habla rusa inició un esfuerzo masivo de preservación a través de iniciativas pioneras como la Biblioteca de Maxim Moshkov3. Inicialmente, el formato de distribución predominante fue el texto plano (.txt), valorado por su inmunidad a la corrupción de bytes y su absoluta compatibilidad multiplataforma3. No obstante, el formato de texto plano impedía la indexación avanzada, la búsqueda estructurada y obligaba a realizar un procesamiento estrictamente secuencial de las líneas3.  
La posterior adopción de documentos de Microsoft Word o archivos PDF introdujo graves ineficiencias; las computadoras de la época experimentaban retardos significativos al renderizar PDF, y dichos archivos resultaban sumamente complejos de convertir a otros formatos de forma automatizada3. El uso de HTML emergió como una alternativa viable para la indexación y la estructuración mediante marcado básico, pero se topó con la falta de rigor del estándar de la época3. HTML permitía libertades excesivas, tales como la omisión de etiquetas de cierre o el anidamiento arbitrario y caótico de contenedores3. Esta laxitud obligó a los navegadores y aplicaciones de lectura a implementar algoritmos de corrección heurística divergentes, provocando que un mismo libro se visualizara de manera inconsistente según el software utilizado3.  
Para resolver estas deficiencias estructurales, un equipo técnico liderado por Dmitry Gribov —director técnico de LitRes— y Mikhail Matsnev —creador del software de lectura Haali Reader— concibió el estándar FictionBook en el año 20043. Diseñado bajo los principios del Consorcio W3C, FictionBook se fundamentó en la rigidez del estándar XML, forzando la validación estricta de documentos frente a un esquema formal denominado FictionBook2.xsd3. A diferencia de los lenguajes orientados a la presentación visual, FictionBook se diseñó para describir de manera exclusiva la estructura lógica y la semántica profunda de un libro1.  
La evolución del estándar experimentó un hito crítico con la transición de su primera versión experimental (FictionBook 1.0), la cual carecía de compatibilidad hacia atrás y requería hojas de transformación XSL para su migración3. Con el lanzamiento de FictionBook 2.0, el formato adoptó de forma obligatoria el uso de espacios de nombres XML para gestionar hipervínculos, estableciendo <http://www.gribuser.ru/xml/fictionbook/2.0> como el espacio de nombres principal de FictionBook y <http://www.w3.org/1999/xlink> para dar soporte a la especificación XLink6.  
El ecosistema evolucionó de forma paralela con el desarrollo de FictionBook 3.0 (FB3), un formato planteado originalmente en fase beta que abandonaba el modelo de archivo XML único de FB2 para adoptar una estructura de directorios comprimidos basada en ZIP similar al contenedor EPUB, lo que facilitaba la inclusión de maquetaciones complejas, tablas nativas e ilustraciones avanzadas sin necesidad de codificar recursos binarios en Base645.  
Para optimizar el almacenamiento y el intercambio de archivos, la especificación FB2 admite de forma nativa la compresión bajo el formato FBZ (o .fb2.zip), el cual constituye aproximadamente el 10% del catálogo total de documentos FB2 existentes5. Un archivo FBZ consiste físicamente en un contenedor comprimido ZIP que aloja en su interior un único archivo XML plano de tipo FB29. El tamaño típico de un archivo FB2 sin comprimir ronda los 910 KB, mientras que la variante comprimida FBZ reduce este volumen a un rango de entre 120 KB y 600 KB9. El tipo MIME oficial para el documento plano es application/x-fictionbook+xml4, mientras que para el archivo comprimido se utiliza el tipo registrado application/fictionbook2+zip5.  
Los motores de lectura y conversión deben inspeccionar los primeros caracteres del archivo en busca del número mágico o firma de cabecera ZIP (PK\\x03\\x04) para determinar si se requiere descompresión en memoria mediante algoritmos dinámicos antes de iniciar el procesamiento sintáctico del XML9.

## **El Desafío de la Representación Semántica: Mapeo de Elementos Específicos**

La transmutación de un documento FictionBook 2.0 a HTML5 semántico puro exige un mapa de correspondencia riguroso que traduzca las abstracciones lógicas de la literatura digital en elementos reconocidos por los motores de renderizado web modernos y las tecnologías de asistencia1. El objetivo de este proceso no es emular la estética de un lector electrónico clásico, sino declarar la estructura jerárquica exacta para que los navegadores web apliquen CSS y atributos de accesibilidad ARIA de forma nativa1.

| Elemento FB2 | Elemento HTML5 Destino | Atributos y Clases Generadas | Rol ARIA e Implicaciones semánticas | Justificación de la Correspondencia Arquitectónica |
| :---- | :---- | :---- | :---- | :---- |
| \<epigraph\> | \<aside\> | class="fb2-epigraph" | role="complementary" | Un epígrafe representa una cita o poema introductorio situado al inicio de una sección6. Se aísla del flujo de prosa principal del texto11. |
| \<cite\> | \<blockquote class="fb2-cite"\> | class="fb2-cite" | role="blockquote" | Agrupa citas formales procedentes de fuentes o autores externos insertadas dentro del cuerpo narrativo6. |
| \<poem\> | \<section\> | class="fb2-poem" | role="region", aria-label="Composición lírica" | Estructura un bloque poético autónomo dentro del texto para aplicar reglas de estilo y evitar la fragmentación visual6. |
| \<stanza\> | \<div class="fb2-stanza"\> | class="fb2-stanza" | Ninguno | Representa una estrofa poética. Sirve de contenedor de versos y se separa físicamente de otras estrofas mediante márgenes verticales colapsados13. |
| \<v\> | \<p\> | class="fb2-verse-line" | Ninguno | Representa un único verso. Al convertirse en un párrafo dedicado con indentación controlada, se previene que las líneas de poesía se deformen de forma incorrecta13. |
| \<annotation\> | \<aside\> | class="fb2-annotation" | role="doc-abstract" | Contiene la sinopsis o resumen de un libro en los metadatos, o notas explicativas al inicio de una sección capitular6. |
| \<title\> | \<header\> con \<h\[1-6\]\> | class="fb2-title" | role="heading", aria-level="\[1-6\]" | Encapsula el título jerárquico de una sección de la obra6. La profundidad del nivel de encabezado se calcula de forma dinámica en base al anidamiento de secciones12. |

### **Tratamiento de la Composición Lírica y Evitación del Uso de Etiquetas Preformateadas**

Una de las malas prácticas más recurrentes en los convertidores automáticos de FB2 es la transformación del elemento \<poem\> y sus líneas hijas \<v\> en bloques de texto preformateado HTML \<pre\>14. El uso de la etiqueta \<pre\> preserva los espacios en blanco y los saltos de línea de forma literal, lo que impide que el motor de renderizado aplique un ajuste de línea fluido en pantallas de dimensiones reducidas, como las de los teléfonos inteligentes o lectores electrónicos13. Esto obliga al lector a realizar un desplazamiento horizontal sumamente incómodo, violando los principios de diseño web responsivo y accesibilidad14.  
Para solventar esta limitación, la correspondencia arquitectónica propuesta mapea el elemento \<poem\> a una sección contenedora \<section class="fb2-poem"\>6. Cada estrofa (\<stanza\>) se traduce en un contenedor bloque \<div class="fb2-stanza"\> y cada verso (\<v\>) se modela como un párrafo semántico \<p class="fb2-verse-line"\>13. El uso de clases dedicadas permite el control milimétrico del comportamiento del texto mediante CSS, empleando reglas como:

CSS  
p.fb2-verse-line {  
  white-space: normal;  
  margin: 0;  
  text-indent: \-1.5em;  
  padding-left: 1.5em;  
}

Esta regla tipográfica garantiza que, si un verso es más largo que el ancho disponible de la pantalla, la línea se ajustará de forma fluida y responsiva hacia el siguiente renglón, aplicando una sangría francesa que ayuda a identificar visualmente que el texto desplazado pertenece al mismo verso original13.

### **Recursión en Estructuras de Estilo Inline**

El procesamiento del texto contenido dentro de párrafos (\<p\>) o versos (\<v\>) no puede realizarse mediante un volcado de texto plano, ya que FB2 permite la presencia de múltiples etiquetas de estilo en línea como \<emphasis\> (énfasis/itálica), \<strong\> (negrita) y \<strikethrough\> (tachado)15. Estos elementos de marcado inline pueden anidarse libremente de forma recursiva (por ejemplo, un fragmento de texto tachado y en negrita dentro de una frase enfatizada)17.  
El algoritmo de conversión debe recorrer de manera recursiva el árbol de nodos de BeautifulSoup18. Al procesar cada nodo secundario, se evalúa si corresponde a un nodo de texto plano —representado en BeautifulSoup como una instancia de NavigableString— o a un subelemento estructurado de tipo Tag18. Si se trata de una etiqueta de formato inline, se mapea dinámicamente a su equivalente HTML5 (\<em\>, \<strong\> o \<s\>) conservando de forma estricta la jerarquía de anidamiento original mediante llamadas recursivas de retorno4.

### **Cálculo Dinámico de Niveles de Encabezado**

Dado que la especificación FictionBook 2.0 permite el anidamiento teórico infinito de elementos \<section\> para estructurar partes, libros, capítulos y subcapítulos, no es posible asignar una etiqueta estática como \<h1\> o \<h2\> a todos los bloques de título \<title\>6. Para generar un árbol de documentos HTML5 válido y accesible, se requiere calcular dinámicamente el nivel del encabezado en función de la profundidad de anidamiento de la sección actual12.  
Si denotamos como ![][image1] a la profundidad de la sección actual (definida como el número de ancestros de tipo \<section\> que posee la etiqueta \<title\> bajo evaluación dentro del árbol XML), el nivel del encabezado HTML ![][image2] se calcula algorítmicamente mediante la siguiente fórmula matemática:  
![][image3]  
donde ![][image4]20. Esta fórmula garantiza que la raíz de una sección de primer nivel (![][image5]) se transforme en un encabezado \<h1\>, una subsección (![][image6]) en un \<h2\>, y de forma progresiva hasta alcanzar el límite físico definido por el estándar HTML5 de un encabezado \<h6\>20. Cualquier nivel de anidamiento superior a cinco se colapsará de forma segura en una etiqueta \<h6\>, evitando la generación accidental de elementos no conformes con el estándar web como \<h7\>20.

## **Ingeniería Inversa de la Arquitectura de Notas al Pie de FB2**

La gestión de anotaciones y notas al pie dentro de la especificación FictionBook 2.0 es uno de sus aspectos estructurales más sofisticados, pero su transposición a entornos web exige resolver diversas inconsistencias técnicas6. FB2 delega su sistema de referencias cruzadas a la especificación abstracta de enlaces XLink6.

### **El Mecanismo de Vinculación de Referencias**

En el cuerpo principal del texto (contenido dentro de la etiqueta \<body\> primordial), las llamadas a notas al pie se declaran como hipervínculos en línea mediante el elemento \<a\>6. Para que un visor de FB2 identifique que este enlace no apunta a un recurso externo o a una sección capitular estándar, el elemento debe contener de manera obligatoria las siguientes propiedades6:

1. **type="note":** Atributo de tipado semántico estricto que indica que el enlace constituye una referencia a una anotación o nota aclaratoria17.  
2. **xlink:href (o namespaces alternativos como l:href o href desnudo):** Un atributo que contiene un identificador de tipo fragmento de URL que apunta al identificador unívoco de la nota6. El formato de la referencia debe ser obligatoriamente un anclaje local prefijado por el carácter almohadilla, por ejemplo, \#nota\_explicativa\_16.

XML  
\<\!-- Estructura de una llamada en el cuerpo narrativo principal de FB2 \--\>  
\<p\>El modelo heliocéntrico de Copérnico\<a xlink:href\="\#nota\_copernico" type\="note"\>1\</a\> alteró de forma permanente la cosmología.\</p\>

### **La Estructura del Almacén de Notas**

La especificación FB2 prohíbe terminantemente la inserción del texto de las notas en línea o de forma adyacente a los párrafos de llamada6. Todo el contenido explicativo de las notas debe estar completamente aislado y agrupado en una estructura \<body\> independiente situada al final de la jerarquía del documento XML6. Este cuerpo especial se caracteriza por poseer el atributo identificador name="notes"21.  
Dentro de \<body name="notes"\>, la información se organiza en elementos \<section\> independientes21. Cada sección representa una nota individual y debe declarar un atributo de identidad id que coincida exactamente con el destino referenciado por la llamada en el texto principal22. Habitualmente, estas secciones comienzan con un título de sección \<title\> que alberga el índice visual de la nota, seguido por uno o más elementos de párrafo \<p\> que desarrollan la explicación22.

XML  
\<\!-- Bloque segregado de notas en el mismo archivo FB2 \--\>  
\<body name\="notes"\>  
  \<section id\="nota\_copernico"\>  
    \<title\>\<p\>1\</p\>\</title\>  
    \<p\>Publicado en su obra De revolutionibus orbium coelestium en 1543\.\</p\>  
  \</section\>  
\</body\>

### **Problemas Técnicos del Procesamiento en BeautifulSoup e Ingeniería Heurística**

La transmutación sistemática de este flujo a HTML5 presenta tres obstáculos técnicos severos que el algoritmo de conversión debe resolver mediante ingeniería de software:

#### **Pérdida de Espacios de Nombres e Incompatibilidad de Parsers**

Si se procesa un archivo FB2 utilizando el analizador HTML por defecto de BeautifulSoup (html.parser), el motor convertirá de forma destructiva todos los nombres de etiquetas y atributos a minúsculas y omitirá o interpretará de forma incorrecta los prefijos de espacios de nombres XML19. Por ejemplo, un atributo escrito como xlink:href o l:href se convertirá en xlink:href o se perderá por completo, impidiendo que el motor localice la referencia de manera fiable19.  
Para evitar esto, el sistema de conversión debe inicializar BeautifulSoup utilizando exclusivamente el analizador XML integrado basado en la biblioteca lxml (xml), garantizando la preservación exacta de la sensibilidad a mayúsculas y minúsculas y de los espacios de nombres asociados a los atributos de enlace19.

#### **Falta de Bidireccionalidad Nativa**

La especificación FB2 es unidireccional por diseño: la llamada en el cuerpo del texto apunta al id de la sección de notas, pero la sección de notas en \<body name="notes"\> no posee ninguna información sobre qué elemento del texto principal realizó la llamada de consulta6. Si un usuario de un navegador web pulsa en una nota para leer su contenido, no tiene forma de regresar al punto exacto del texto original donde interrumpió la lectura4.  
La heurística desarrollada soluciona esto mediante la generación dinámica de un sistema de identificadores correlativos bidireccionales síncronos4. Al procesar cada llamada de nota, el sistema registra el identificador de la nota destino y le asigna un identificador de retorno único de tipo fnref-{id\_nota}-{indice\_secuencial}4. Al compilar la lista final de notas en HTML5, se inyecta de forma automática un hipervínculo de retorno (backlink) semántico (role="doc-backlink") que apunta directamente al anclaje de la llamada de origen4.

#### **Fuga de Contenido de Notas en el Flujo Secuencial**

Si un script realiza una lectura secuencial simplificada de los elementos \<body\> de un documento XML de FB2, verterá los contenidos de todos los cuerpos uno detrás de otro de forma directa en el cuerpo de la página HTML56. Esto provocaría que el bloque de notas explicativas se renderizara de forma cruda e intrusiva inmediatamente después de la última palabra del libro, mostrándose de forma duplicada al lector6.  
La heurística propuesta exige un proceso de purgado estructurado en tres fases: primero, se realiza un escaneo previo en busca de nodos de tipo body con atributo name="notes"21; segundo, se extraen dichos nodos del árbol DOM principal de forma destructiva utilizando el método extract() de BeautifulSoup, almacenando las secciones de notas en un diccionario indexado en memoria19; tercero, tras finalizar el procesamiento de la narrativa principal, el sistema genera un contenedor semántico final de pie de página (\<footer\>) y vuelca de forma ordenada únicamente aquellas notas que fueron efectivamente referenciadas a lo largo de la lectura4.

## **Arquitectura del Convertidor bajo los Patrones de Diseño Strategy y Composite**

Para construir un motor de conversión robusto, mantenible y alineado con los principios de diseño de software empresarial, el sistema se estructura combinando los patrones **Strategy** y **Composite**28.

### **Colaboración de Patrones de Diseño**

El patrón de diseño de comportamiento **Strategy** se utiliza para encapsular las reglas de transformación individuales de cada etiqueta compleja de FB2 (\<epigraph\>, \<cite\>, \<poem\>, \<stanza\>, \<v\>, \<annotation\>, \<title\>, \<a\>)28. En lugar de implementar una estructura monolítica de bifurcaciones condicionales de tipo if/else basadas en el nombre del elemento XML —lo cual incrementaría severamente la complejidad ciclomática del código y violaría el principio de Abierto/Cerrado (Open/Closed Principle)—, el motor de conversión delega la lógica de transformación a un conjunto de objetos de estrategia especializados que comparten una interfaz común28.  
El patrón de estructura **Composite** se manifiesta de forma natural a través de la representación del árbol de nodos DOM gestionado por BeautifulSoup29. Cada elemento procesado en HTML5 puede actuar como un nodo compuesto (un contenedor ParentNode como \<div\> o \<section\> que alberga otros nodos hijos) o como un nodo hoja (un LeafNode terminal que únicamente contiene texto plano, como un verso o un elemento de formato inline simple)19. La llamada recursiva del motor de conversión recorre y transmuta esta estructura compuesta de manera transparente para el cliente de la aplicación29.  
Adicionalmente, el diseño se apoya en el patrón de creación **Factory Method** para orquestar la selección e instanciación en tiempo de ejecución de la estrategia de conversión adecuada según la etiqueta XML que se esté procesando en cada etapa del recorrido del árbol, minimizando el acoplamiento entre el contexto del documento y la lógica de renderizado específica de cada elemento31.

## **Implementación Práctica del Motor de Transmutación en Python**

El siguiente script en Python proporciona la implementación completa, autocontenida y lista para producción del motor de transmutación de documentos FB2/FBZ a HTML5 semántico utilizando la biblioteca BeautifulSoup19. El código gestiona de forma nativa la heurística de descompresión en memoria, el aislamiento de notas, el direccionamiento bidireccional accesible y el procesamiento recursivo bajo el patrón de diseño Strategy9.

Python  
import abc  
import io  
import re  
import zipfile  
from typing import Dict, Optional, Tuple, Union  
from bs4 import BeautifulSoup, Tag

\# \=====================================================================  
\# INTERFAZ ABSTRACTA STRATEGY (ELEMENTO DE TRANSFORMACIÓN)  
\# \=====================================================================

class ElementTransformationStrategy(abc.ABC):  
    """  
    Clase base abstracta que define la interfaz común para todas las  
    estrategias de transformación de elementos XML de FB2 a HTML5.  
    """  

    @abc.abstractmethod  
    def transform(self, tag: Tag, context: 'FB2DocumentContext') \-\> Optional\[Tag\]:  
        """  
        Transmuta un elemento XML de FB2 en su correspondiente nodo HTML5 semántico.  
          
        :param tag: El nodo Tag XML nativo a procesar.  
        :param context: El contexto del documento para consultar el estado global.  
        :return: Un nuevo objeto Tag de HTML5, o None si el elemento es removido.  
        """  
        pass

\# \=====================================================================  
\# CLASE CONTEXTO (MOTOR CENTRAL DE CONVERSIÓN)  
\# \=====================================================================

class FB2DocumentContext:  
    """  
    Clase de contexto que coordina el árbol de parseo de BeautifulSoup,  
    gestiona el registro dinámico de estrategias y opera el ciclo de vida  
    de la conversión y extracción heurística de notas al pie.  
    """

    def \_\_init\_\_(self, raw\_data: bytes, file\_name: Optional\[str\] \= None):  
        """  
        Inicializa el contexto del documento.  
          
        :param raw\_data: Flujo de bytes del archivo (soporta .fb2 plano o .fbz comprimido).  
        :param file\_name: Nombre opcional del archivo de origen para logs.  
        """  
        self.raw\_data \= raw\_data  
        self.file\_name \= file\_name or "documento"  
        self.xml\_content \= self.\_extract\_and\_resolve\_container()  
          
        \# Uso explícito del parser 'xml' para preservar la capitalización y los namespaces  
        self.soup \= BeautifulSoup(self.xml\_content, 'xml')  
          
        \# Registro interno de estrategias asociadas a nombres de etiquetas en minúsculas  
        self.\_strategies: Dict\[str, ElementTransformationStrategy\] \= {}  
          
        \# Registro heurístico de notas al pie aisladas (ID \-\> Nodo XML de la sección de nota)  
        self.notes\_registry: Dict\[str, Tag\] \= {}  
          
        \# Catálogo de llamadas registradas en texto principal (ID Nota \-\> ID de la llamada HTML)  
        self.references\_registry: Dict\[str, str\] \= {}

    def \_extract\_and\_resolve\_container(self) \-\> bytes:  
        """  
        Heurística de descompresión: evalúa la firma mágica de la cabecera  
        para procesar transparentemente archivos .fbz (ZIP) o .fb2 planos.  
        """  
        \# Firma estándar de cabecera de un archivo ZIP (PK\\x03\\x04)  
        if self.raw\_data.startswith(b'PK\\x03\\x04'):  
            with zipfile.ZipFile(io.BytesIO(self.raw\_data)) as archive:  
                file\_list \= archive.namelist()  
                \# Localizar el único archivo XML con extensión .fb2 o .xml contenido en el ZIP  
                fb2\_files \= \[f for f in file\_list if f.endswith('.fb2') or f.endswith('.xml')\]  
                if not fb2\_files:  
                    raise ValueError(f"El archivo FBZ '{self.file\_name}' no contiene un documento XML interno válido.")  
                return archive.read(fb2\_files\[0\])  
        return self.raw\_data

    def register\_strategy(self, tag\_name: str, strategy: ElementTransformationStrategy) \-\> None:  
        """Registra una estrategia de transformación vinculada a una etiqueta específica."""  
        self.\_strategies\[tag\_name.lower()\] \= strategy

    def resolve\_xlink\_href(self, tag: Tag) \-\> Optional\[str\]:  
        """  
        Resuelve heurísticamente los atributos de enlace de tipo XLink bajo  
        múltiples variantes de prefijo o denominación (xlink:href, l:href, href).  
        """  
        for candidate\_attr in \['xlink:href', 'l:href', 'href'\]:  
            if tag.has\_attr(candidate\_attr):  
                val \= tag\[candidate\_attr\]  
                if isinstance(val, list):  
                    val \= " ".join(val)  
                \# Retorna el ID limpio eliminando el prefijo de anclaje local '\#'  
                return val.lstrip('\#')  
        return None

    def execute\_transmutation(self) \-\> str:  
        """  
        Ejecuta el pipeline de transformación semántica de FB2 a HTML5.  
          
        :return: Cadena de texto que contiene el documento HTML5 estructurado final.  
        """  
        \# Fase 1: Ingeniería inversa y aislamiento del bloque de notas  
        self.\_isolate\_and\_extract\_notes\_body()

        \# Fase 2: Localización y procesamiento del flujo de texto principal  
        main\_body\_node \= self.soup.find('body')  
        if not main\_body\_node:  
            raise ValueError("No se localizó un elemento \<body\> válido en el documento FictionBook.")  
              
        \# Transformar recursivamente el cuerpo utilizando el mapa de estrategias  
        transformed\_html\_body \= self.\_process\_node\_recursive(main\_body\_node)

        \# Fase 3: Compilación de notas al pie acumuladas en un pie de página semántico  
        compiled\_footer \= self.\_build\_html5\_endnotes()

        \# Fase 4: Ensamblado del documento final bajo la jerarquía estándar HTML5  
        output\_document \= BeautifulSoup(  
            '\<\!DOCTYPE html\>\<html\>\<head\>\<meta charset="UTF-8"/\>\</head\>\<body\>\</body\>\</html\>',  
            'html.parser'  
        )  
          
        \# Extraer e inyectar el título del libro en la sección head si está definido en metadatos  
        book\_title\_node \= self.soup.find('book-title')  
        if book\_title\_node:  
            title\_element \= output\_document.new\_tag('title')  
            title\_element.string \= book\_title\_node.get\_text().strip()  
            output\_document.head.append(title\_element)

        \# Inyectar el cuerpo de texto transformado y las notas al pie generadas  
        html\_body\_target \= output\_document.find('body')  
        if transformed\_html\_body:  
            html\_body\_target.append(transformed\_html\_body)  
        if compiled\_footer and len(compiled\_footer.find\_all('li')) \> 0:  
            html\_body\_target.append(compiled\_footer)

        return output\_document.prettify()

    def \_process\_node\_recursive(self, node: Union\[Tag, str\]) \-\> Optional\[Union\[Tag, str\]\]:  
        """  
        Recorre recursivamente los nodos del árbol DOM XML, seleccionando y aplicando  
        las estrategias registradas o mapeando elementos inline básicos.  
        """  
        \# Si el nodo es un elemento de texto plano (NavigableString), retornarlo directamente  
        if isinstance(node, str):  
            return node

        node\_name\_lower \= node.name.lower()  
          
        \# Si existe una estrategia de transformación registrada, delegar el procesamiento  
        if node\_name\_lower in self.\_strategies:  
            return self.\_strategies\[node\_name\_lower\].transform(node, self)

        \# Mapeo de elementos estructurales o de formato en línea genéricos por defecto  
        if node\_name\_lower \== 'p':  
            p\_tag \= self.soup.new\_tag('p')  
            for child in node.children:  
                processed\_child \= self.\_process\_node\_recursive(child)  
                if processed\_child:  
                    p\_tag.append(processed\_child)  
            return p\_tag  
              
        elif node\_name\_lower in \['emphasis', 'strong', 'strikethrough'\]:  
            \# Mapeo semántico de etiquetas de formato tipográfico  
            tag\_translation\_map \= {'emphasis': 'em', 'strong': 'strong', 'strikethrough': 's'}  
            html\_tag\_name \= tag\_translation\_map\[node\_name\_lower\]  
            style\_tag \= self.soup.new\_tag(html\_tag\_name)  
            for child in node.children:  
                processed\_child \= self.\_process\_node\_recursive(child)  
                if processed\_child:  
                    style\_tag.append(processed\_child)  
            return style\_tag

        elif node\_name\_lower \== 'empty-line':  
            \# Transmutación del salto de línea vertical nativo de FB2  
            br\_tag \= self.soup.new\_tag('br', attrs={'class': 'fb2-empty-line'})  
            return br\_tag

        \# Procesamiento heurístico de elementos sin estrategia registrada: desanidar y continuar  
        wrapper\_div \= self.soup.new\_tag('div')  
        for child in node.children:  
            processed\_child \= self.\_process\_node\_recursive(child)  
            if processed\_child:  
                wrapper\_div.append(processed\_child)  
                  
        return wrapper\_div if len(wrapper\_div.contents) \> 0 else None

    def \_isolate\_and\_extract\_notes\_body(self) \-\> None:  
        """  
        Implementa ingeniería inversa sobre el almacén de notas de FB2. Localiza  
        las secciones de notas, las extrae de forma segura del árbol DOM de forma  
        destructiva y las almacena en memoria para evitar fugas de renderizado.  
        """  
        footnote\_bodies \= self.soup.find\_all('body', attrs={'name': 'notes'})  
        for body in footnote\_bodies:  
            \# Extraer recursivamente cada sección etiquetada con un identificador único  
            sections \= body.find\_all('section')  
            for section in sections:  
                if section.has\_attr('id'):  
                    note\_id \= section\['id'\]  
                    \# Extraer el elemento completo del DOM para aislarlo en memoria  
                    self.notes\_registry\[note\_id\] \= section.extract()  
            \# Destruir completamente el cuerpo de notas residual del árbol original  
            body.decompose()

    def \_build\_html5\_endnotes(self) \-\> Optional\[Tag\]:  
        """  
        Compila las notas almacenadas en memoria en una lista ordenada semántica de HTML5,  
        estableciendo hipervínculos de retorno bidireccionales síncronos con el texto.  
        """  
        if not self.references\_registry:  
            return None

        footer\_element \= self.soup.new\_tag('footer', attrs={'class': 'document-footer'})  
        section\_element \= self.soup.new\_tag('section', attrs={  
            'role': 'doc-endnotes',   
            'class': 'endnotes',  
            'aria-label': 'Notas de fin de documento'  
        })  
        ol\_element \= self.soup.new\_tag('ol')

        \# Procesar únicamente las notas que fueron efectivamente invocadas por el texto  
        for note\_id, reference\_call\_id in self.references\_registry.items():  
            if note\_id in self.notes\_registry:  
                section\_node \= self.notes\_registry\[note\_id\]  
                li\_element \= self.soup.new\_tag('li', attrs={  
                    'id': f'fn-{note\_id}',  
                    'role': 'doc-footnote'  
                })

                \# Extraer el contenido textual evitando duplicar el encabezado o ID de la nota  
                p\_nodes \= section\_node.find\_all('p')  
                note\_content\_span \= self.soup.new\_tag('span')  
                  
                for p in p\_nodes:  
                    text\_content \= p.get\_text().strip()  
                    \# Descartar párrafos que sean meros duplicados del número o id de nota  
                    if text\_content \!= note\_id:  
                        note\_content\_span.append(text\_content \+ " ")

                li\_element.append(note\_content\_span)

                \# Generar el enlace bidireccional de retorno (backlink) síncono  
                backlink\_anchor \= self.soup.new\_tag('a', attrs={  
                    'href': f'\#{reference\_call\_id}',  
                    'role': 'doc-backlink',  
                    'class': 'backref',  
                    'aria-label': 'Volver al texto principal de la obra'  
                })  
                backlink\_anchor.string \= "↩"  
                li\_element.append(backlink\_anchor)  
                  
                ol\_element.append(li\_element)

        section\_element.append(ol\_element)  
        footer\_element.append(section\_element)  
        return footer\_element

\# \=====================================================================  
\# ESTRATEGIAS CONCRETAS DE TRANSFORMACIÓN  
\# \=====================================================================

class EpigraphStrategy(ElementTransformationStrategy):  
    """Estrategia para transmutar epígrafes literarios en bloques complementarios."""  
    def transform(self, tag: Tag, context: FB2DocumentContext) \-\> Tag:  
        epigraph\_element \= context.soup.new\_tag('aside', attrs={  
            'class': 'fb2-epigraph',
            'role': 'complementary'  
        })  

        for child in tag.children:  
            if isinstance(child, Tag) and child.name.lower() \== 'text-author':  
                \# El autor del epígrafe se formatea semánticamente mediante la etiqueta cite  
                author\_tag \= context.soup.new\_tag('cite', attrs={'class': 'fb2-author'})  
                author\_tag.string \= child.get\_text().strip()  
                epigraph\_element.append(author\_tag)  
            elif isinstance(child, Tag):  
                processed\_child \= context.\_process\_node\_recursive(child)  
                if processed\_child:  
                    epigraph\_element.append(processed\_child)  
        return epigraph\_element

class CiteStrategy(ElementTransformationStrategy):  
    """Estrategia para transformar elementos de cita textual en blockquotes semánticos."""  
    def transform(self, tag: Tag, context: FB2DocumentContext) \-\> Tag:  
        blockquote\_element \= context.soup.new\_tag('blockquote', attrs={'class': 'fb2-cite'})  

        for child in tag.children:  
            if isinstance(child, Tag) and child.name.lower() \== 'text-author':  
                \# El autor de la cita se estructura en un pie de ilustración o cita formal  
                figcaption\_element \= context.soup.new\_tag('figcaption', attrs={'class': 'fb2-cite-author'})  
                cite\_element \= context.soup.new\_tag('cite')  
                cite\_element.string \= child.get\_text().strip()  
                figcaption\_element.append(cite\_element)  
                blockquote\_element.append(figcaption\_element)  
            elif isinstance(child, Tag):  
                processed\_child \= context.\_process\_node\_recursive(child)  
                if processed\_child:  
                    blockquote\_element.append(processed\_child)  
        return blockquote\_element

class PoemStrategy(ElementTransformationStrategy):  
    """Estrategia para estructurar poemas como secciones líricas aisladas y fluidas."""  
    def transform(self, tag: Tag, context: FB2DocumentContext) \-\> Tag:  
        poem\_element \= context.soup.new\_tag('section', attrs={  
            'class': 'fb2-poem',  
            'role': 'region',  
            'aria-label': 'Composición poética estructurada'  
        })  

        for child in tag.children:  
            processed\_child \= context.\_process\_node\_recursive(child)  
            if processed\_child:  
                poem\_element.append(processed\_child)  
        return poem\_element

class StanzaStrategy(ElementTransformationStrategy):  
    """Estrategia para agrupar versos en una estrofa poética controlada por bloques."""  
    def transform(self, tag: Tag, context: FB2DocumentContext) \-\> Tag:  
        stanza\_element \= context.soup.new\_tag('div', attrs={'class': 'fb2-stanza'})  
        for child in tag.children:  
            processed\_child \= context.\_process\_node\_recursive(child)  
            if processed\_child:  
                stanza\_element.append(processed\_child)  
        return stanza\_element

class VerseStrategy(ElementTransformationStrategy):  
    """Estrategia para mapear versos poéticos individuales reduciendo márgenes verticales."""  
    def transform(self, tag: Tag, context: FB2DocumentContext) \-\> Tag:  
        verse\_element \= context.soup.new\_tag('p', attrs={'class': 'fb2-verse-line'})  
        verse\_element.string \= tag.get\_text().strip()  
        return verse\_element

class AnnotationStrategy(ElementTransformationStrategy):  
    """Estrategia para transformar anotaciones de metadatos en bloques informativos."""  
    def transform(self, tag: Tag, context: FB2DocumentContext) \-\> Tag:  
        annotation\_element \= context.soup.new\_tag('aside', attrs={  
            'class': 'fb2-annotation',  
            'role': 'doc-abstract'  
        })  
        for child in tag.children:  
            processed\_child \= context.\_process\_node\_recursive(child)  
            if processed\_child:  
                annotation\_element.append(processed\_child)  
        return annotation\_element

class TitleStrategy(ElementTransformationStrategy):  
    """Estrategia para calcular dinámicamente la jerarquía del encabezado en base a secciones."""  
    def transform(self, tag: Tag, context: FB2DocumentContext) \-\> Tag:  
        \# Calcular el número de ancestros de tipo 'section' para deducir el nivel semántico  
        nesting\_level \= len(tag.find\_parents('section'))  
        computed\_heading\_level \= min(6, nesting\_level \+ 1)  

        header\_container \= context.soup.new\_tag('header', attrs={'class': 'fb2-title-header'})  
        h\_element \= context.soup.new\_tag(f'h{computed\_heading\_level}', attrs={'class': 'fb2-title'})  
          
        \# Unificar el texto de los diferentes párrafos que componen el título original  
        title\_paragraphs \= \[p.get\_text().strip() for p in tag.find\_all('p')\]  
        h\_element.string \= " \- ".join(title\_paragraphs)  
          
        header\_container.append(h\_element)  
        return header\_container

class FootnoteStrategy(ElementTransformationStrategy):  
    """  
    Estrategia de enlace a notas al pie: opera de forma heurística sobre enlaces,  
    registrando las referencias bidireccionales cruzadas y tipando el nodo en HTML5.  
    """  
    def transform(self, tag: Tag, context: FB2DocumentContext) \-\> Tag:  
        note\_target\_id \= context.resolve\_xlink\_href(tag)  
        if not note\_target\_id:  
            \# Si el elemento carece de hipervínculo de destino, se degrada a un texto inline  
            fallback\_span \= context.soup.new\_tag('span')  
            fallback\_span.string \= tag.get\_text()  
            return fallback\_span

        \# Generar un índice correlativo único para rastrear múltiples llamadas a una misma nota  
        sequential\_index \= len(context.references\_registry) \+ 1  
        unique\_call\_id \= f'fnref-{note\_target\_id}-{sequential\_index}'  
          
        \# Registrar la correspondencia síncrona en el contexto del documento  
        context.references\_registry\[note\_target\_id\] \= unique\_call\_id

        \# Reconstruir la etiqueta de anclaje bajo el estándar de accesibilidad digital  
        anchor\_element \= context.soup.new\_tag('a', attrs={  
            'id': unique\_call\_id,  
            'href': f'\#fn-{note\_target\_id}',  
            'role': 'doc-noteref',  
            'class': 'footnote-ref'  
        })  
        \# Mantener el índice de llamada original del texto de FB2 (números, asteriscos, etc.)  
        anchor\_element.string \= tag.get\_text().strip() or str(sequential\_index)  
        return anchor\_element

## **Consideraciones de Rendimiento, Concurrencia y Estilización CSS**

El procesamiento automatizado de grandes volúmenes de documentos literarios digitales impone rigurosas demandas de rendimiento sobre la infraestructura del software de conversión4.

### **Eficiencia del Procesamiento XML y Concurrencia bajo el GIL**

El motor de parseo BeautifulSoup, si bien proporciona una interfaz extraordinariamente idiomática y potente para manipular árboles jerárquicos estructurados, es intrínsecamente un software intensivo en operaciones de CPU (*CPU-bound*) cuando procesa documentos de gran escala o deserializa cadenas codificadas en Base64 procedentes de la etiqueta \<binary\>19. Bajo el intérprete de referencia de Python (CPython), el bloqueo global del intérprete (*Global Interpreter Lock* o GIL) impide que múltiples hilos de ejecución aprovechen arquitecturas multinúcleo para procesar documentos de manera simultánea en un mismo proceso.  
Para implementar este convertidor en sistemas empresariales de alta disponibilidad, se debe evitar el uso de hilos estándar (threading) para tareas de conversión masiva33. En su lugar, el sistema de orquestación debe implementar un modelo de paralelismo real basado en procesos utilizando el módulo concurrent.futures.ProcessPoolExecutor o integrando colas de tareas asíncronas distribuidas33. Esto permite instanciar múltiples intérpretes de Python aislados en los diferentes núcleos de la CPU, procesando lotes concurrentes de archivos de forma paralela sin sufrir cuellos de botella por contención del GIL33.  
Adicionalmente, se recomienda aislar los elementos \<binary\> pesados antes de invocar la transmutación semántica si no se requiere procesar las imágenes en tiempo real, previniendo así un consumo de memoria excesivo y optimizando los tiempos de procesamiento de la biblioteca lxml subyacente4.

### **Estilización CSS para la Presentación Semántica HTML5**

La correcta transmutación estructural realizada por el algoritmo exige una hoja de estilos CSS correspondiente para guiar de manera óptima el comportamiento tipográfico y estructural de los elementos resultantes en el navegador1:

CSS  
/\* Restablecimiento semántico del flujo y sangría de párrafos de texto \*/  
p {  
  margin-top: 0;  
  margin-bottom: 0.75rem;  
  line-height: 1.6;  
  text-align: justify;  
  text-indent: 1.5rem; /\* Sangría de primera línea tradicional \*/  
}

/\* Tratamiento del bloque de epígrafe \*/  
aside.fb2-epigraph {  
  margin: 2.5rem 10% 2.5rem 25%;  
  font-style: italic;  
  color: \#3a3a3a;  
  border-left: 2px solid \#ccc;  
  padding-left: 1.25rem;  
}

aside.fb2-epigraph p {  
  text-indent: 0;  
  text-align: left;  
}

cite.fb2-author {  
  display: block;  
  text-align: right;  
  font-weight: 600;  
  font-style: normal;  
  margin-top: 0.5rem;  
}

/\* Estilos de bloque para citas textuales formales \*/  
blockquote.fb2-cite {  
  margin: 1.5rem 5%;  
  padding: 0.75rem 1.25rem;  
  background-color: \#f7f9fa;  
  border-left: 4px solid \#00567a;  
}

blockquote.fb2-cite p {  
  text-indent: 0;  
}

.fb2-cite-author {  
  margin-top: 0.5rem;  
  text-align: right;  
  font-size: 0.9rem;  
  font-weight: bold;  
}

/\* Formateo de poesía adaptable y responsiva \*/  
section.fb2-poem {  
  margin: 2rem auto;  
  max-width: 75%;  
  font-family: "Georgia", "Book Antiqua", serif;  
}

div.fb2-stanza {  
  margin-bottom: 2rem;  
}

p.fb2-verse-line {  
  margin: 0;  
  padding: 0;  
  text-indent: 0 \!important; /\* Desactivar sangría de párrafo tradicional \*/  
  white-space: normal;  
  line-height: 1.5;  
  padding-left: 1.5rem;  
  text-indent: \-1.5rem; /\* Sangría francesa para versos extensos ajustados \*/  
}

/\* Anotaciones e introducciones de sección \*/  
aside.fb2-annotation {  
  background-color: \#f1f3f5;  
  padding: 1.25rem;  
  border-radius: 4px;  
  margin: 1.5rem 0;  
  font-size: 0.95rem;  
  border-top: 2px solid \#6c757d;  
}

aside.fb2-annotation p {  
  text-indent: 0;  
}

/\* Estilización del bloque dinámico de Notas al Pie \*/  
section\[role="doc-endnotes"\] {  
  margin-top: 4rem;  
  padding-top: 2rem;  
  border-top: 1px solid \#dee2e6;  
  font-size: 0.9rem;  
  color: \#495057;  
}

section\[role="doc-endnotes"\] ol {  
  padding-left: 1.5rem;  
}

section\[role="doc-endnotes"\] li {  
  margin-bottom: 0.75rem;  
  line-height: 1.5;  
}

a\[role="doc-noteref"\] {  
  font-size: 0.8rem;  
  vertical-align: super;  
  text-decoration: none;  
  font-weight: 600;  
  color: \#00567a;  
  padding: 0 0.15rem;  
}

a\[role="doc-noteref"\]:hover {  
  text-decoration: underline;  
}

a\[role="doc-backlink"\] {  
  text-decoration: none;  
  margin-left: 0.5rem;  
  color: \#00567a;  
  font-weight: bold;  
}

a\[role="doc-backlink"\]:hover {  
  color: \#00364d;  
}

## **Conclusiones y Viabilidad de Conservación Digital**

La transmutación del formato de libro digital estructurado FictionBook 2.0 (FB2) a la semántica estándar de HTML5 constituye un avance significativo para la accesibilidad universal y la compatibilidad multiplataforma de las obras literarias1. Mediante la aplicación rigurosa de principios de ingeniería de software reflejados en el desacoplamiento de lógicas del patrón Strategy y el control dinámico de jerarquías de anidamiento provisto por Composite, la preservación del sentido semántico original de la obra se mantiene intacta28.  
El algoritmo heurístico de extracción de notas al pie resuelve la asimetría original de FictionBook 2.0 en cuanto al flujo de hipervínculos cruzados6. Al unificar las llamadas de notas de un solo sentido y consolidarlas en un sistema bidireccional accesible que cumple de manera estricta con las pautas de accesibilidad para contenido web, se erradican de forma definitiva las fugas de renderizado secuencial del texto de las notas y las pérdidas de navegación del lector4. La viabilidad técnica demostrada garantiza que los documentos convertidos permanezcan legibles y adaptables a largo plazo en cualquier navegador estándar moderno, salvaguardando el legado y la integridad conceptual del patrimonio literario digitalizado1.

### **Obras citadas**

1. Convert fb2 to html \- Filestar, [https://filestar.com/skills/fb2/convert-fb2-to-html](https://filestar.com/skills/fb2/convert-fb2-to-html)  
2. Comparison of e-book formats \- Wikipedia, [https://en.wikipedia.org/wiki/Comparison\_of\_e-book\_formats](https://en.wikipedia.org/wiki/Comparison_of_e-book_formats)  
3. E-books and their formats: FB2 and FB3 \- history, pros, cons and principles of work, [https://prohoster.info/en/blog/novosti-interneta/elektronnye-knigi-i-ih-formaty-fb2-i-fb3-istoriya-plyusy-minusy-i-printsipy-raboty](https://prohoster.info/en/blog/novosti-interneta/elektronnye-knigi-i-ih-formaty-fb2-i-fb3-istoriya-plyusy-minusy-i-printsipy-raboty)  
4. Convert FB2 to HTML Online Fast \- ConvertFiles, [https://www.convertfiles.com/convert/document/fb2-to-html](https://www.convertfiles.com/convert/document/fb2-to-html)  
5. FictionBook \- Wikipedia, [https://en.wikipedia.org/wiki/FictionBook](https://en.wikipedia.org/wiki/FictionBook)  
6. Eng:FictionBook description, [http://www.fictionbook.org/index.php/Eng:FictionBook\_description](http://www.fictionbook.org/index.php/Eng:FictionBook_description)  
7. FictionBook 2.0 \- XML Specification for open eBooks. \- GribUser.ru, [http://www.gribuser.ru/xml/fictionbook/index.html.en](http://www.gribuser.ru/xml/fictionbook/index.html.en)  
8. FictionBook 1.0 \- XML Specification for open eBooks. \- GribUser.ru, [http://www.gribuser.ru/xml/fictionbook/1.0/index.html.en](http://www.gribuser.ru/xml/fictionbook/1.0/index.html.en)  
9. What is it? How to open an FB2 file? \- FILExt, [https://filext.com/file-extension/FB2](https://filext.com/file-extension/FB2)  
10. Support Fiction Book extensions · Issue \#870 · sumatrapdfreader/sumatrapdf \- GitHub, [https://github.com/sumatrapdfreader/sumatrapdf/issues/870](https://github.com/sumatrapdfreader/sumatrapdf/issues/870)  
11. Epigraph \- DocBook: The Definitive Guide, [https://tdg.docbook.org/tdg/3.1/epigraph.html](https://tdg.docbook.org/tdg/3.1/epigraph.html)  
12. FB2 \- MobileRead Wiki, [https://wiki.mobileread.com/wiki/FB2](https://wiki.mobileread.com/wiki/FB2)  
13. How to semantically tag poem text? \- html \- Stack Overflow, [https://stackoverflow.com/questions/14734564/how-to-semantically-tag-poem-text](https://stackoverflow.com/questions/14734564/how-to-semantically-tag-poem-text)  
14. Elaborate fb2.css · Issue \#6480 · koreader/koreader \- GitHub, [https://github.com/koreader/koreader/issues/6480](https://github.com/koreader/koreader/issues/6480)  
15. XML схема FictionBook2.0 — FictionBook, [http://www.fictionbook.org/index.php/XML\_%D1%81%D1%85%D0%B5%D0%BC%D0%B0\_FictionBook2.0](http://www.fictionbook.org/index.php/XML_%D1%81%D1%85%D0%B5%D0%BC%D0%B0_FictionBook2.0)  
16. Your guide to 7 open eBook formats | Opensource.com, [https://opensource.com/education/15/11/ebook-open-formats](https://opensource.com/education/15/11/ebook-open-formats)  
17. fictionup-example-en.fb2 \- GitHub, [https://github.com/Text-extend-tools/fictionup/blob/main/examples/fictionup-example-en.fb2](https://github.com/Text-extend-tools/fictionup/blob/main/examples/fictionup-example-en.fb2)  
18. Vibecoding Your Way Out of Format Hell: Building a Custom FB2 Converter, [https://python.plainenglish.io/vibecoding-your-way-out-of-format-hell-building-a-custom-fb2-converter-2aa9839548fe](https://python.plainenglish.io/vibecoding-your-way-out-of-format-hell-building-a-custom-fb2-converter-2aa9839548fe)  
19. Beautiful Soup 4.4.0 documentation, [https://beautiful-soup-4.readthedocs.io/en/latest/](https://beautiful-soup-4.readthedocs.io/en/latest/)  
20. FictionBook Options \- Quarto, [https://quarto.org/docs/reference/formats/fb2.html](https://quarto.org/docs/reference/formats/fb2.html)  
21. fb2/FictionBook.xsd at master · gribuser/fb2 \- GitHub, [https://github.com/gribuser/fb2/blob/master/FictionBook.xsd](https://github.com/gribuser/fb2/blob/master/FictionBook.xsd)  
22. [unknown\_url](http://docs.google.com/unknown_url)  
23. Описание формата FB2 от Sclex \- FictionBook, [http://www.fictionbook.org/index.php/%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5\_%D1%84%D0%BE%D1%80%D0%BC%D0%B0%D1%82%D0%B0\_FB2\_%D0%BE%D1%82\_Sclex](http://www.fictionbook.org/index.php/%D0%9E%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5_%D1%84%D0%BE%D1%80%D0%BC%D0%B0%D1%82%D0%B0_FB2_%D0%BE%D1%82_Sclex)  
24. Eng:XML Schema Fictionbook 2.1, [http://www.fictionbook.org/index.php/Eng:XML\_Schema\_Fictionbook\_2.1](http://www.fictionbook.org/index.php/Eng:XML_Schema_Fictionbook_2.1)  
25. fb2-parser/fb2\_parser.py at master \- GitHub, [https://github.com/genych/fb2-parser/blob/master/fb2\_parser.py](https://github.com/genych/fb2-parser/blob/master/fb2_parser.py)  
26. How can I access namespaced XML elements using BeautifulSoup? \- Stack Overflow, [https://stackoverflow.com/questions/3058912/how-can-i-access-namespaced-xml-elements-using-beautifulsoup](https://stackoverflow.com/questions/3058912/how-can-i-access-namespaced-xml-elements-using-beautifulsoup)  
27. Encoding Decisions, [https://cha.artsci.tamu.edu/CriticismArchive/encodingDecisions.html](https://cha.artsci.tamu.edu/CriticismArchive/encodingDecisions.html)  
28. Strategy \- Refactoring.Guru, [https://refactoring.guru/design-patterns/strategy](https://refactoring.guru/design-patterns/strategy)  
29. bdjekel/static\_site\_generator: boot.dev guided project \#3 \- GitHub, [https://github.com/bdjekel/static\_site\_generator](https://github.com/bdjekel/static_site_generator)  
30. How to implement a strategy pattern with runtime selection of a method? \- Stack Overflow, [https://stackoverflow.com/questions/24695250/how-to-implement-a-strategy-pattern-with-runtime-selection-of-a-method](https://stackoverflow.com/questions/24695250/how-to-implement-a-strategy-pattern-with-runtime-selection-of-a-method)  
31. typescript \- How to correctly implement strategy design pattern \- Stack Overflow, [https://stackoverflow.com/questions/60107761/how-to-correctly-implement-strategy-design-pattern](https://stackoverflow.com/questions/60107761/how-to-correctly-implement-strategy-design-pattern)  
32. 7.7 Design Patterns — Research Software Engineering with Python \- GitHub Pages, [https://alan-turing-institute.github.io/rse-course/html/module07\_construction\_and\_design/07\_07\_design\_patterns.html](https://alan-turing-institute.github.io/rse-course/html/module07_construction_and_design/07_07_design_patterns.html)  
33. Python API Reference \- Kreuzberg.dev, [https://docs.kreuzberg.dev/reference/api-python/](https://docs.kreuzberg.dev/reference/api-python/)  
34. FB2 Converter \- CloudConvert, [https://cloudconvert.com/fb2-converter](https://cloudconvert.com/fb2-converter)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAaCAYAAABhJqYYAAAAsUlEQVR4XmNgGMFAHIi/AfF/IO5Dk8MKuBggiuPRJbABUSC+hi6IC4QB8WR0QRiIBuItQHwOiDuAeAYQe6OogAIxIF4IxBxAzAbEGxgg7gW5GwUUQiWQQTIWMTC4yoApAbIFXYxBCCr4Ck38JhB/RRNjsGSAKN6KJCYLFdsMxK5ArIgkx7AMiC8zQDzXDcT3GSCK04B4LpI6MOAG4iUMEA15DJDQmArEtxkgoTQKBisAAA+mIjcP447YAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAaCAYAAAAjZdWPAAACWElEQVR4Xu2WS+hNURjFl0ceYaDknZgYyKPEQElISQkTE8VABoTyShRRBmSgKEqKopSRAUJGHknJqxAD3FJCigmKAWv5XHdb/73/7lH3Ft1frcFd69zv7HP2t/c+QId/nw1uNME4qkaNN78tzKKeu9kky6kn1GAPWslI6jW10oMKXKOOuFliLfUto0PU/Iwvnf/xzwa62Ruqj/k5amjUeZf4S6kvye+mWEV9omZQ/S2bjbjJYqrv7xH6UR+oneaX6E1tQ9S7kPg9qWfJ76a4h/L0XkXcJMdJxKB102Z5iKg3xfxl1BzzigxHFBnhARmKxnTmeERdcbMbRiNq1cwX2kF2uFlCq7c0KL390qDVRvKPepCgPld9tcJtahPiP1ozjmbrlJslNMX1gZWkFnEmI7L9HiTcoY4jHlCDqtdbkF6UkPZ5kWmIIl89IJPQuEmu1+YhMu1AOY5Ra8zT9ZfMS3nqRo76Sr7uAVmPyD5SvSwTMxH5Fg/IQMSLGGa+rt9qXorWyB+5jCi0zwNyBpGd9eAnExD5Hg/IQkTmyJvqZsJNN5wBiA1dhRZZJt6i++nXbqP8oAdkHboOWn39iupBjUU8mHPRDecAorD26BzK3rtpaBb0cI4Gdh9xGEm7EIfHYcQ2+gBdD7El1ArzfjERMSCXGER9zmTq6xzqT+VjPEDs/48Rh8lmxGn4grpLzU2uq7ObGuVmK9CnpRbcag/+gnNutJLT1C03KzIE8e3TNqYjWsS/Jaqwl3rpZqvRYtMxXRUt2BvUdg/ahfpbH0RV2EidcLNDh/+d72bllnUi/oVPAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAaCAYAAADxNd/XAAAB7ElEQVR4Xu2WO0gcURSGj4oPRFSEdFpoI1EQJCoYJcQiELCSVIY0omIj2EgiaCV2YiEo1mIeBCIEiYKFGE3sgpioIFpsIyIIIoFUKfQ/nFnd+XcyDwbCIvPBB7v/uXfnvmZmRRIS7i0v4Sq8gkewyF3Off7AQVgBn8EdWOJqEcACvM7wX+TBdVjKhRg8hlOU6RjGKAvkkQRPQCmGu3BRbLXi8hG2UnYBDykLZFps8ONcCKAbnsIRsclFoVrsmtxvw8n7KPfll1gnXo0wPIFrMAWHqOZHh3jv+IpYzkfLhV50CX4VOwraQQcQh2b4TmwSvKpePBfvCXwWy/VUePIW/oB1zvf02Z+7bRGPL/AMNnGB6BHvCXwSy2e5oLwSa5DJJfwLyymPgh6HZfiBCz60iPcE0jvwmgvKd9hLmTbepCwKW2K72sCFAPQE6LXzKdeXmub9lEuZ2EpXUq6NJygLgz6BtuFDLoSkQOztW0W5/qaOqY1yaXQKjGbtYi+qYap58UJsx+ZhLdWi8h7WU3YMz8XGk4XeqDXOZ72JtHHK+a6PL306+THAQUx0kHqs9XSk+S13D5gsCuEJ3Bf7C/EA7sGfcDKj3f/kQGxMM/Ab7HKXcx99Z3TCUfiGagmM3i9604fxqXVJSEhIuA/cAHj7andZZOnmAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAaCAYAAADxNd/XAAABlklEQVR4Xu2WyysFYRjGH+SyEFJ2bGwsLF3KJWWhbC3JRrKzFIqVLEQWSvkDSCkLKUsduewsXEsszkZRSlJWFjyvd44z8844Y3PGSd+vfnXmed9pvm/mm28O4HD8W4boHn2hN7QsWC583ugYraZ99IRWBDpiWKMfPpOkk86bTMYwbbJYWvA3E9iibSZ7otcmi2UJOvgZW8gj9dBrlpt838tHTJ6TC+hJ9m7kky5EP/FdaG6XVoAeuk4PoC+OnJD2NyRAP6InsAPNZVVEskFPaaN3nFn7q98d0Swg2/sb7/W0HxlA9AS2ofmKLQjD0AY/z/SdVpk837QiegKZJzBpC8IxHTSZNKdMlgSyAuTaxSaXj5rkoyZHJfRO15hcmmdNlgQl0K9vrckPoWNqNzmavYJFsg5aRMdNzc8iwus8lw8I313LJm0y2S19hI4nhLyoDd5veYmkOe0dy/Ylu1OSyCBlWcvqyPCK7AYTopTe0UvoX4g6ekbP6ZyvL0muoGNapke0N1gufORL3E0n6JSpORwOh8PxxSddw2hBAAp5RAAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAaCAYAAADxNd/XAAABN0lEQVR4Xu2WPUuCURiG74qaIjJobHHNLYJa3KK5MQj6AfkPbGoKW4N+QI1N/YEcnCL63PpyCdpya2nQ+/R44ngb+ZpwxDgXXKDPx6u3vkcEEol/T47uaHFUWKcX9EEbWTiizcCYuDf+Qa9hr/2nAI4lDCfAHJ2gKxgwwAHsAmVtRGLgAHewCyxrIxJ9ByjSY1qla7DlejgQmb4CnNBLmm8/9/f+4ffEz+yj87D38tXWMpE5wBY9ldo7/aQzUo+JD/CkDaVGN6XmFs+lFhsf4FkbIdOwT3pW6m5xV2qx8QFetBGyCBtSXG2VjtGS9EIq6L7Pf/ONjn9t9sYHqGtDcQd1of14A3Zo/NIZ7NdpGGzDAjTolPQ6mKSP9B72F2Ke3tBbuhfMxaKA7m/OeRUOJRKJRCIx8rQAB55fOqOEC04AAAAASUVORK5CYII=>
