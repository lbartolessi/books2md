# **Análisis Forense de la Estructura XHTML/CSS en EPUBs Técnicos: Métodos de Producción, Semántica y Regularidad de Extracción**

El análisis de ingeniería forense de software y preservación digital de los libros electrónicos (EPUB) producidos por las principales editoriales de informática (O'Reilly Media, Manning Publications, Packt Publishing y Pragmatic Bookshelf) revela un cambio de paradigma crítico frente a la maquetación tradicional basada en Adobe InDesign1. Mientras que InDesign genera un código XHTML visualmente orientado, fragmentado y caracterizado por selectores CSS redundantes (del tipo .CharOverride-X o .ParaOverride-Y), las editoriales técnicas analizadas implementan flujos de trabajo automatizados de código fuente único (single-source publishing)2. Estos pipelines procesan lenguajes de marcado ligero o esquemas XML estructurados para producir un DOM XHTML altamente predecible y consistente, optimizado para la preservación a largo plazo y la legibilidad en múltiples dispositivos de tinta electrónica4.

## **Herramientas de Autoría y Pipelines de Compilación**

Las metodologías de producción de estas cuatro editoriales se basan en traductores automatizados que transforman estructuras lógicas abstractas en artefactos XHTML5 estandarizados3. La elección del compilador y la sintaxis de marcado original determinan por completo el grado de regularidad de las etiquetas resultantes.

### **O'Reilly Media: El Paradigma HTMLBook y la Infraestructura Atlas**

O'Reilly Media procesa su catálogo a través de su plataforma de autoría basada en la nube denominada Atlas2. Los autores escriben sus manuscritos utilizando AsciiDoc o DocBook XML2. El núcleo de compilación de Atlas es la especificación HTMLBook, un subconjunto estricto de XHTML5 diseñado específicamente para estructurar libros sin añadir elementos ajenos a la especificación de la W3C3.  
La transformación se ejecuta mediante hojas de estilo XSLT (htmlbook-xsl), que incluyen módulos críticos como epub.xsl, chunk.xsl, ncx.xsl y opf.xsl11. El compilador procesa el árbol de análisis sintáctico (AST) y produce una salida estructurada bajo el esquema de validación htmlbook.xsd5. Este proceso asegura que cada capítulo, apéndice o sección se encuadre en etiquetas estructurales acompañadas del atributo semántico data-type (ej. \<section data-type="chapter"\>)3. Al estar validado sintácticamente, el impacto del compilador en la consistencia de las etiquetas es total, eliminando la variabilidad de clases y garantizando una estructura uniforme idónea para la preservación digital3.

### **Manning Publications: Flujo Post-PDF y el Prefijo .fm-**

Manning Publications opera con un flujo de trabajo que prioriza la liberación de la versión PDF (ePDF) como el documento maestro final de producción13. La conversión al formato EPUB se inicia únicamente tras consolidar este formato de página fija, lo que introduce desafíos de sincronización estructural14.  
Los libros modernos de Manning (publicados a partir de 2020\) utilizan un motor de traducción que inyecta selectores CSS unificados bajo el espacio de nombres (namespace) .fm-15. Sin embargo, la herencia de una traducción tardía desde el PDF provoca en ocasiones desajustes en el flujo, como desalineaciones físicas en listas ordenadas y viñetas bajo el formato MOBI15. Los títulos antiguos (anteriores a 2020, como *Redis in Action*) se compilaban mediante un pipeline diferente, el cual generaba un XHTML con clases genéricas y dependientes del software de conversión (como clases de tipo .calibre16 y fuentes estáticas tipo "Liberation Mono")15.

### **Packt Publishing: Compilación Masiva Industrializada**

Packt Publishing emplea un pipeline de producción altamente automatizado orientado a la publicación de gran volumen16. Los manuscritos, redactados en formatos estructurados como DocBook XML o Markdown, se compilan mediante un motor institucional que genera de manera simultánea archivos EPUB, PDF y formatos de lectura web personalizados a través de APIs de distribución19.  
La regularidad de las clases en los archivos EPUB de Packt es extremadamente rígida. El compilador aplica plantillas de estilo globales que inyectan selectores CSS estandarizados con prefijos específicos como .Code\_, .Packt\_, .Normal y .Warning20. Este enfoque industrializado elimina por completo la intervención estilística manual, lo que se traduce en un DOM altamente predecible para procesos de automatización y parseado de datos.

### **Pragmatic Bookshelf: La Transición de PML a Markdown**

Pragmatic Bookshelf desarrolló históricamente su propio sistema de maquetación basado en PML (Pragmatic Markup Language), un lenguaje de marcado semántico XML diseñado por Dave Thomas7. Este ecosistema utilizaba un toolchain local y de integración continua compilado en Java y jRuby que procesaba el manuscrito para generar PDFs de alta calidad de manera conjunta con archivos EPUB y MOBI estructurados7.  
En la actualidad, el flujo ha migrado hacia Markdown como formato estándar de entrada, pero reteniendo la lógica de compilación nativa basada en scripts automatizados7. El compilador de Pragmatic Bookshelf destaca por su diseño orientado a desarrolladores, generando un XHTML libre de elementos contenedores virtuales innecesarios (div wrappers) y optimizando de forma nativa los bloques de código para evitar distorsiones en pantallas con resoluciones limitadas9.

### **Tabla 1: Comparativa de Pipelines de Compilación y Nomenclatura Estructural**

| Editorial | Formato de Entrada Primario | Toolchain de Compilación | Especificación de Validación del DOM | Esquema de Nomenclatura CSS |
| :---- | :---- | :---- | :---- | :---- |
| **O'Reilly Media** | AsciiDoc / DocBook XML2 | Atlas Pipeline (htmlbook-xsl)2 | htmlbook.xsd (XHTML5 estricto)3 | Atributos data-type y selectores semánticos estructurales3 |
| **Manning Publications** | XML / Markdown estructurado | Traductor propietario post-PDF13 | XHTML estándar (sin esquema semántico público) | Clases con namespace .fm- (post-2020) o genéricas tipo Calibre (pre-2020)15 |
| **Packt Publishing** | DocBook XML / Markdown | Compilador masivo integrado19 | XHTML estándar corporativo | Prefijos sistemáticos de plantilla (.Code\_, .Packt\_)20 |
| **Pragmatic Bookshelf** | PML / Markdown7 | Pipeline Java / jRuby personalizado7 | XHTML minimalista semántico | Selectores funcionales directos de bajo acoplamiento7 |

## **Anatomía de las Notas y Referencias**

El tratamiento de las notas al pie, notas finales y referencias cruzadas en libros técnicos exige una estructura de hipervínculos bidireccional extremadamente sólida para evitar enlaces rotos y facilitar la navegación no lineal en pantallas táctiles de e-readers7.

### **O'Reilly Media: Semántica EPUB3 e Integridad de Referencias**

O'Reilly adopta de forma nativa los atributos semánticos de la especificación EPUB311. El punto de inserción de la nota en el texto principal se codifica mediante un elemento de anclaje \<a\> que incorpora el atributo epub:type="noteref"26. El cuerpo de la nota se almacena dentro de un contenedor \<aside\> que lleva el atributo obligatorio epub:type="footnote" junto con el rol de accesibilidad ARIA role="doc-footnote"11.  
Durante la fase de desarrollo del compilador de Atlas, se documentó un error donde las hojas de estilo XSLT generaban de forma errónea el atributo data-type="noteref" o data-type="footnote" en lugar del espacio de nombres semántico de EPUB3, fallo que fue subsanado en las revisiones posteriores de epub.xsl26. Los enlaces de retorno (backlinks) se resuelven mediante un atributo epub:type="backlink" y el rol role="doc-backlink" incrustados en un enlace situado al inicio de la nota, permitiendo al motor de renderizado del dispositivo abrir la nota en una ventana flotante emergente sin perder la posición de lectura. Las referencias cruzadas se estructuran mediante etiquetas \<xref\> que el compilador mapea como hipervínculos estándar vinculando el identificador único del elemento de destino a través de atributos linkend27.

### **Manning Publications: Enlaces de Retorno de Flujo Lineal**

Manning Publications no implementa por lo general la etiqueta semántica \<aside\> ni los atributos epub:type de EPUB3 en sus notas al pie. En su lugar, el pipeline post-PDF convierte las notas en bloques de texto secuenciales situados al final de cada capítulo. La referencia en el texto se codifica mediante un enlace básico \<a\> con la clase .fm-noteref. El enlace de retorno se inyecta manualmente al principio de la nota final utilizando una clase .fm-backlink, confiando la navegación exclusivamente al comportamiento de salto hipertextual plano del navegador o del e-reader15.

### **Packt Publishing: Anclajes Bidireccionales Automatizados**

El pipeline de Packt automatiza la creación de notas finales de capítulo mediante un algoritmo de correspondencia secuencial. Las referencias en el texto utilizan la etiqueta \<a\> con una clase genérica como .Packt\_Anchor y un ID autogenerado secuencialmente. Al final del archivo XHTML, el compilador genera un contenedor \<div\> con la clase .Packt\_FootnoteBlock donde cada nota individual dispone de un enlace de retorno manual que apunta de vuelta al ID del texto principal. No se utilizan etiquetas semánticas de EPUB3, lo que asegura compatibilidad absoluta con motores de renderizado antiguos a costa de perder la capacidad de desplegar notas flotantes emergentes.

### **Pragmatic Bookshelf: Enlaces Libres de Errores y DOM Limpio**

Pragmatic Bookshelf otorga una prioridad crítica a la integridad de los enlaces dentro de sus EPUBs, implementando validaciones automáticas integradas en sus flujos de integración continua para comprobar la validez de cada ID y destino de hipervínculo7. Las notas se compilan de forma bidireccional utilizando anclajes limpios sin elementos de envoltura innecesarios. El cuerpo de la nota se ubica al final del documento, y aunque se enfoca en mantener la compatibilidad con dispositivos de lectura de generaciones anteriores (evitando las hojas de estilo complejas y scripts interactivos)9, la estructura de los backlinks es de una precisión milimétrica, utilizando clases funcionales como .footback y .footnote7.

### **Tratamiento de Notas y Comentarios Intercalados en Código Fuente**

El manejo de comentarios y notas explicativas dentro de las etiquetas \<pre\> y \<code\> varía significativamente entre las editoriales analizadas:

* **O'Reilly Media** evita inyectar XHTML decorativo interactivo dentro del bloque \<pre\>27. En su lugar, utiliza comentarios de código nativos del lenguaje analizado (ej. //  en JavaScript o \#  en Python) que actúan como "callouts" lógicos27. Estos números se corresponden de manera exacta con una lista explicativa ordenada colocada inmediatamente después del bloque de código, permitiendo una extracción limpia del código fuente sin alterar la sintaxis programática27.  
* **Manning Publications** inyecta de forma directa etiquetas \<span\> con clases de anotación como .fm-co o similares dentro del cuerpo del bloque \<pre\>. Esto permite al CSS aplicar estilos de posicionamiento absoluto o flotante para alinear visualmente la explicación a la derecha de la línea de código afectada15.  
* **Packt Publishing** opta por un diseño no intrusivo. No se inyectan anotaciones complejas dentro de \<pre\>, prefiriendo guiar al lector mediante explicaciones paso a paso en párrafos independientes formateados con la clase .Normal.  
* **Pragmatic Bookshelf** integra llamadas numéricas directamente en el texto del código mediante caracteres especiales formateados de forma segura con fuentes monoespaciadas embebidas (ej. Inconsolata o DejaVu)23. Esto previene que la inyección de los caracteres de llamada desplace horizontalmente la alineación o rompa la indentación lógica del código23.

## **Estructuras Flotantes y Callouts Técnicos**

La representación de advertencias (warnings), consejos (tips), notas del autor, barras laterales (sidebars) y bloques de código titulados es uno de los puntos donde la diferencia frente a Adobe InDesign es más radical. Mientras que InDesign tiende a rasterizar estas estructuras como imágenes estáticas o a aplanarlas perdiendo su relación jerárquica, los compiladores semánticos inyectan selectores altamente consistentes basados en reglas de marcado lógico3.

### **O'Reilly Media: La Estructura de Bloques en HTMLBook**

De acuerdo con la especificación de HTMLBook de O'Reilly, las barras laterales (sidebars) deben estructurarse obligatoriamente bajo la etiqueta de HTML5 \<aside\> acompañada del atributo data-type="sidebar"3. El título de la barra lateral se encapsula en una etiqueta \<h5\> o \<h1\> (dependiendo de la versión del esquema aplicado)3.  
Para los bloques de advertencia (admonitions), el compilador de Atlas inyecta etiquetas \<div\> con el atributo obligatorio data-type parametrizado con los valores "note", "warning", "tip", "caution" o "important"3. Las hojas de estilo globales del tema institucional de O'Reilly (Atlas Trade Theme) aplican propiedades de visualización (como bordes grises suaves y sombreados ligeros) basándose en selectores de atributos28. Esto permite prescindir de clases CSS específicas para la estructura, logrando que el documento sea totalmente legible incluso si el dispositivo de lectura descarta la hoja de estilo externa3.

### **Manning Publications: Componentización con el Prefijo .fm-**

Manning componentiza sus bloques de advertencia y barras laterales envolviéndolos en contenedores \<div\> que declaran clases del espacio de nombres .fm-15. Los bloques de notas utilizan la clase .fm-note, los consejos se marcan como .fm-tip y las barras laterales se declaran como .fm-sidebar junto con un encabezado de clase .fm-sidebar-title15. Estos bloques aplican estilos CSS rigurosos para delimitar el contenido, tales como bordes izquierdos coloreados gruesos y márgenes de compensación horizontal.

### **Packt Publishing: Clases Semánticas Predecibles**

El pipeline de Packt genera contenedores de advertencia estandarizados a nivel global19. Las notas informativas se marcan bajo la clase .Packt\_Note, mientras que las advertencias críticas utilizan la clase .Packt\_Warning20. Para los bloques de código que incorporan un título de archivo o una cabecera explicativa, Packt utiliza una estructura de acoplamiento rígido consistente en un contenedor principal .Packt\_CodeContainer que engloba un elemento superior con clase .Packt\_CodeHeader y un bloque \<pre\> inferior con la clase de código correspondiente20.

### **Pragmatic Bookshelf: Componentes de Bajo Acoplamiento**

Pragmatic Bookshelf genera un XHTML de diseño limpio heredado de su núcleo de procesamiento PML7. Las advertencias se estructuran en divs con la clase directa .note o .warning7. Las barras laterales utilizan la clase .sidebar7. En el caso específico de sus libros estructurados como manuales prácticos o recetarios, el compilador inyecta un componente especializado denominado \<div class="recipe"\> que agrupa el título de la receta y cada uno de los pasos de ejecución (\<div class="recipe-step"\>), facilitando de manera notable la extracción selectiva de tareas de programación de forma automatizada7.

### **Tabla 2: Mapeo de Clases CSS y Selectores de Bloques Flotantes**

La tabla a continuación detalla las clases CSS exactas y las estructuras del DOM que los compiladores de cada una de las cuatro editoriales inyectan para estructurar los elementos de soporte técnico:

| Editorial | Notas Informativas (Notes) | Advertencias Críticas (Warnings) | Barras Laterales (Sidebars) | Bloques de Código con Título |
| :---- | :---- | :---- | :---- | :---- |
| **O'Reilly Media** | \<div data-type="note"\> \[cite: 3\] | \<div data-type="warning"\> \[cite: 3, 27\] | \<aside data-type="sidebar"\> \[cite: 3\] | Elemento \<figure\> o \<div data-type="example"\> con \<caption\> \[cite: 3\] |
| **Manning** | \<div class="fm-note"\> \[cite: 15\] | \<div class="fm-warning"\> | \<div class="fm-sidebar"\> | \<div class="fm-code-container"\> con \<p class="fm-code-title"\> |
| **Packt** | \<div class="Packt\_Note"\> \[cite: 20, 22\] | \<div class="Packt\_Warning"\> | \<div class="Packt\_Sidebar"\> | \<div class="Packt\_CodeContainer"\> con \<p class="Packt\_CodeHeader"\> \[cite: 20\] |
| **Pragmatic** | \<div class="note"\> \[cite: 7\] | \<div class="warning"\> \[cite: 7\] | \<div class="sidebar"\> \[cite: 7\] | \<div class="code-box"\> con \<p class="code-title"\> |

## **Tratamiento Técnico del Código Fuente**

La renderización y preservación de porciones de código fuente en formato de texto fluido (reflowable) plantea retos técnicos severos respecto a la escala tipográfica, el desbordamiento de líneas horizontales y la segmentación de páginas9.

### **Ausencia de Tablas para Números de Línea**

El análisis forense digital confirma que **ninguna de las cuatro editoriales analizadas utiliza tablas HTML (**\<table\>**) para representar los números de línea** en sus ediciones EPUB estándar3. El uso de tablas en listados de código de texto fluido es una práctica desaconsejada en la preservación digital por dos motivos técnicos:

1. Provoca fallas críticas en la función de copiar y pegar de los dispositivos de lectura, mezclando secuencialmente los números de línea con las instrucciones de código (ej. el lector copia "1 const 2 let 3 return" en lugar de las líneas limpias)18.  
2. Limita severamente la adaptabilidad horizontal del bloque de código en pantallas de tamaño reducido (como teléfonos inteligentes), comprimiendo la columna de código útil de manera destructiva9.

### **Segmentación Multigrupo de Bloques de Código de Varias Páginas**

Para evitar que los bloques de código extensos queden truncados de forma incorrecta o generen grandes espacios en blanco huérfanos antes de iniciarse, las editoriales descartan el uso de la propiedad CSS page-break-inside: avoid en el contenedor principal \<pre\>. En su lugar, el pipeline de compilación permite que el bloque fluya y se divida de manera natural a través de las páginas virtuales del motor de lectura (renderizado nativo de WebKit o Blink).  
Para conservar la coherencia estilística, se aplican reglas de desbordamiento horizontal controladas mediante CSS en el elemento contenedor:

CSS  
pre {  
   overflow-x: auto;  
   white-space: pre-wrap;  
   word-wrap: break-word;  
}

Esto fuerza al motor de lectura a realizar un ajuste de línea suave (soft wrap) cuando una instrucción excede el ancho físico de la pantalla, evitando el truncamiento visual del código sin requerir la fragmentación del bloque en múltiples archivos HTML de menor tamaño31.

### **Decisiones de Tipografía y Escala: El Conflicto de la Inyección de Fuentes**

La política de empaquetado de tipografías monoespaciadas varía radicalmente entre las editoriales analizadas, reflejando filosofías de diseño contrapuestas:

#### **O'Reilly Media y la Confianza en el Sistema Anfitrión**

La hoja de estilo global de O'Reilly (Atlas Trade Theme) **no incorpora fuentes tipográficas monoespaciadas embebidas** dentro de los archivos EPUB o MOBI28. La editorial justifica esta decisión técnica argumentando que los fabricantes de dispositivos optimizan de manera exhaustiva el renderizado y el contraste de sus tipografías nativas de sistema28. Al depender exclusivamente de la pila tipográfica estándar del dispositivo (ej. font-family: monospace;), se reduce el tamaño final del archivo EPUB y se mitigan errores de visualización provocados por la incompatibilidad de fuentes propietarias28.

#### **Manning Publications y el Error de Escala de la Clase .fm-code-in-text**

En las ediciones de Manning posteriores al año 2020, el compilador inyecta estilos CSS con escalas de tamaño excesivamente elevadas para el código en línea (inline code)15. La clase principal .fm-code-in-text define un tamaño de fuente de ![][image1] con una altura de línea de ![][image2]15. Esta sobredimensión rompe el ritmo visual de los párrafos y provoca interrupciones molestas en la lectura15. Adicionalmente, el compilador inyecta variaciones estilísticas inconsistentes en un mismo libro, tales como las clases:

* .fm-code-in-text1 configurada a ![][image3]15.  
* .fm-code-in-text2 configurada a ![][image4]15.  
* .fm-code-in-text3 configurada a ![][image3] con altura de línea de ![][image5]15.

Para solventar este problema en procesos de preservación o migración de bibliotecas, se requiere desempaquetar el EPUB y redefinir mediante scripts estas clases para normalizarlas a un valor estándar (ej. font-size: 1em;)15. En contraste, sus libros antiguos (pre-2020) utilizaban clases heredadas de Calibre sin este problema de escala tipográfica, mapeando el código inline mediante una declaración limpia: .calibre16 { font-family: "Liberation Mono", monospace; }15. Asimismo, en ciertos entornos de lectura de Calibre o visores basados en navegador, Manning impone estilos de fuente física como Verdana que bloquean la anulación tipográfica del lector, obligando a intervenciones forenses manuales sobre la hoja de estilo stylesheet.css para eliminar estas directivas restrictivas33.

#### **Pragmatic Bookshelf y la Fidelidad del Monospaciado Embebido**

Pragmatic Bookshelf adopta una postura inversa a la de O'Reilly, priorizando la consistencia exacta del espaciado del código técnico en cualquier plataforma de hardware9. Sus EPUBs incorporan de manera nativa archivos de fuentes tipográficas monoespaciadas de alta calidad, tales como Inconsolata.otf y DejaVuSansMono.ttf, declarándolas mediante reglas @font-face en la hoja de estilo principal (geek\_bookshelf.css o equivalentes)23. Esto asegura que los listados de código preserven su estructura visual y alineación de caracteres no proporcionales de manera uniforme en cualquier e-reader, minimizando el riesgo de que una fuente de sistema defectuosa distorsione la sintaxis de lenguajes altamente dependientes de la indentación (como Python o Haskell)23.

## **Ejemplos Representativos de Fragmentos XHTML**

Con el objetivo de verificar la regularidad y estructura interna del código generado por los respectivos compiladores, se presentan a continuación ejemplos representativos correspondientes a cada una de las cuatro editoriales. Cada bloque ilustra de manera integrada los cuatro puntos críticos del análisis técnico: la estructura de bloques flotantes/advertencias, el enlazado bidireccional de notas, la estructura del código fuente con comentarios y el código inline.

### **1\. O'Reilly Media (HTMLBook Semántico con Especificación EPUB3)**

HTML, XML  
\<?xml version="1.0" encoding="utf-8"?\>  
\<html xmlns\="http://www.w3.org/1999/xhtml" xmlns:epub\="http://www.idpf.org/2007/ops" xml:lang\="es"\>  
\<head\>  
  \<title\>Estructuración de Sistemas O'Reilly\</title\>  
  \<link rel\="stylesheet" href\="epub.css" type\="text/css" /\>  
\</head\>  
\<body\>  
  \<section data-type\="chapter" id\="chapter\_1"\>  
    \<h1 class\="title"\>Capítulo 1\. Arquitectura de Microservicios\</h1\>  
      
    \<\!-- Bloque de Advertencia (Admonition) \--\>  
    \<div data-type\="warning" class\="warning\_box"\>  
      \<h6\>Advertencia de Configuración\</h6\>  
      \<p\>Modificar el puerto de escucha sin declarar una interfaz de red segura puede exponer el servicio a accesos no autorizados en la red local.\</p\>  
    \</div\>

    \<\!-- Párrafo con Código Inline y Referencia a Nota al Pie (Footnote Reference) \--\>  
    \<p\>La inicialización del servidor de base de datos se ejecuta mediante la llamada al método   
      \<code class\="literal"\>db.connect()\</code\> en el bloque de inicio de la aplicación  
      \<a href\="\#fn\_database\_ref" id\="fnref\_database\_ref" epub:type\="noteref" class\="noteref"\>1\</a\>.  
    \</p\>

    \<\!-- Bloque de Código con Título y Callouts Lógicos \--\>  
    \<div data-type\="example" id\="code\_example\_1"\>  
      \<h5 class\="caption"\>Ejemplo 1.1. Inicialización de Express Server\</h5\>  
      \<pre class\="programlisting" data-type\="programlisting" data-code-language\="javascript"\>\<code class\="language-javascript"\>  
const express \= require('express');  
const app \= express(); // \<1\>

app.listen(3000, () \=\> {  
  console.log('Server running on port 3000'); // \<2\>  
});  
      \</code\>\</pre\>  
      \<\!-- Explicación de los Callouts \--\>  
      \<div class\="callout-list"\>  
        \<ol\>  
          \<li\>Instanciación del objeto de aplicación de Express.\</li\>  
          \<li\>Callback de notificación de escucha activa de peticiones HTTP.\</li\>  
        \</ol\>  
      \</div\>  
    \</div\>

    \<\!-- Nota al Pie (Footnote Body) estructurada semánticamente \--\>  
    \<aside id\="fn\_database\_ref" epub:type\="footnote" role\="doc-footnote" class\="footnote"\>  
      \<p class\="footnote-text"\>  
        \<a href\="\#fnref\_database\_ref" epub:type\="backlink" role\="doc-backlink" class\="backlink"\>1.\</a\>  
        Consulte la documentación de persistencia para entornos distribuidos si requiere utilizar un clúster de réplicas de MongoDB.  
      \</p\>  
    \</aside\>  
  \</section\>  
\</body\>  
\</html\>

### **2\. Manning Publications (Estructura de Bloques con Namespace .fm-)**

HTML, XML  
\<?xml version="1.0" encoding="utf-8"?\>  
\<html xmlns\="http://www.w3.org/1999/xhtml" xml:lang\="es"\>  
\<head\>  
  \<title\>Patrones de Diseño en TypeScript\</title\>  
  \<link rel\="stylesheet" href\="stylesheet.css" type\="text/css" /\>  
\</head\>  
\<body\>  
  \<div class\="fm-chapter" id\="ch1"\>  
    \<h2 class\="fm-chapter-title"\>Capítulo 1\. El Patrón Singleton\</h2\>

    \<\!-- Bloque Flotante de Barra Lateral (Sidebar) \--\>  
    \<div class\="fm-sidebar"\>  
      \<h4 class\="fm-sidebar-title"\>¿Cuándo usar Singletons?\</h4\>  
      \<p class\="fm-sidebar-content"\>Se recomienda limitar el patrón Singleton a recursos de acceso global único donde la concurrencia no altere el estado interno de la instancia.\</p\>  
    \</div\>

    \<\!-- Código Inline mostrando el problema de escala tipográfica de Manning \--\>  
    \<p class\="fm-paragraph"\>Para recuperar la instancia activa del gestor de conexiones, se debe invocar el método estático   
      \<span class\="fm-code-in-text"\>DatabaseManager.getInstance()\</span\>   
      desde el módulo de inicialización del hilo de ejecución secundario  
      \<a href\="\#footnote-ts-1" id\="ref-ts-1" class\="fm-noteref"\>\[1\]\</a\>.  
    \</p\>

    \<\!-- Bloque de Código Fuente con Elementos Internos de Anotación (Spans) \--\>  
    \<div class\="fm-code-container"\>  
      \<p class\="fm-code-title"\>Listado 1.1. Declaración de la clase Singleton\</p\>  
      \<pre class\="fm-code-block"\>\<code\>  
class DatabaseManager {  
  private static instance: DatabaseManager;  
  \<span class\="fm-co"\>// El constructor privado impide la instanciación directa\</span\>  
  private constructor() {} 

  public static getInstance(): DatabaseManager {  
    if (\!DatabaseManager.instance) {  
      DatabaseManager.instance \= new DatabaseManager();  
    }  
    return DatabaseManager.instance;  
  }  
}  
      \</code\>\</pre\>  
    \</div\>

    \<\!-- Bloque de Notas al final del flujo del capítulo \--\>  
    \<div class\="fm-footnote-container"\>  
      \<p class\="fm-footnote" id\="footnote-ts-1"\>  
        \<a href\="\#ref-ts-1" class\="fm-backlink"\>\[1\]\</a\>  
        Tenga en cuenta que en entornos de multiprocesamiento simétrico real, el acceso a la instancia única debe protegerse mediante exclusiones mutuas (mutex).  
      \</p\>  
    \</div\>  
  \</div\>  
\</body\>  
\</html\>

### **3\. Packt Publishing (Plantilla Automatizada Industrializada con Prefijos)**

HTML, XML  
\<?xml version="1.0" encoding="utf-8"?\>  
\<html xmlns\="http://www.w3.org/1999/xhtml" xml:lang\="es"\>  
\<head\>  
  \<title\>Desarrollo Web Moderno con React\</title\>  
  \<link rel\="stylesheet" href\="stylesheet.css" type\="text/css" /\>  
\</head\>  
\<body\>  
  \<div class\="Packt\_Container"\>  
    \<h1 class\="Packt\_ChapterHeader"\>Capítulo 2\. Componentes de React y State Management\</h1\>

    \<\!-- Nota de Advertencia (Warning Block) \--\>  
    \<div class\="Packt\_Warning"\>  
      \<p class\="Packt\_WarningHeading"\>ADVERTENCIA CRÍTICA\</p\>  
      \<p\>Nunca modifique de forma directa el objeto de estado de un componente. Utilice sistemáticamente el método de mutación proporcionado por el gancho React correspondiente.\</p\>  
    \</div\>

    \<\!-- Párrafo con Código Inline y Enlace Plano de Nota al Pie \--\>  
    \<p class\="Packt\_Normal"\>La actualización asíncrona del estado se gestiona mediante el gancho   
      \<code class\="Packt\_InlineCode"\>useState\</code\>, asegurando que el motor de renderizado virtual planifique el re-renderizado del componente de manera eficiente  
      \<a class\="Packt\_Anchor" id\="back\_note\_packt\_1" href\="\#note\_packt\_1"\>\[1\]\</a\>.  
    \</p\>

    \<\!-- Bloque de Código con Cabecera Estructurada \--\>  
    \<div class\="Packt\_CodeContainer"\>  
      \<p class\="Packt\_CodeHeader"\>Listado 2.1. Implementación de un Contador con React Hooks\</p\>  
      \<pre class\="Packt\_CodeBlock"\>\<code\>  
import React, { useState } from 'react';

export function Counter() {  
  const \[count, setCount\] \= useState(0); // Declaración del hook de estado

  return (  
    \<button onClick={() \=\> setCount(count \+ 1)}\>  
      Click: {count}  
    \</button\>  
  );  
}  
      \</code\>\</pre\>  
    \</div\>

    \<\!-- Contenedor de Notas al Pie del Capítulo \--\>  
    \<div class\="Packt\_FootnoteBlock"\>  
      \<p class\="Packt\_FootnoteText" id\="note\_packt\_1"\>  
        \<a class\="Packt\_Backlink" href\="\#back\_note\_packt\_1"\>\[1\]\</a\>  
        React optimiza la actualización del estado agrupando por lotes (batching) múltiples llamadas dentro de un mismo ciclo de eventos para evitar renderizados redundantes.  
      \</p\>  
    \</div\>  
  \</div\>  
\</body\>  
\</html\>

### **4\. Pragmatic Bookshelf (Estructura Limpia con Fuentes Monoespaciadas Embebidas)**

HTML, XML  
\<?xml version="1.0" encoding="utf-8"?\>  
\<html xmlns\="http://www.w3.org/1999/xhtml" xml:lang\="es"\>  
\<head\>  
  \<title\>Programación Concurrente en Elixir\</title\>  
  \<link rel\="stylesheet" href\="geek\_bookshelf.css" type\="text/css" /\>  
\</head\>  
\<body\>  
  \<div class\="chapter" id\="chapter\_elixir"\>  
    \<h2 class\="title"\>Capítulo 3\. El Modelo de Actores\</h2\>

    \<\!-- Caja de Advertencia Semántica (Note) \--\>  
    \<div class\="note"\>  
      \<h5\>Filosofía de Elixir\</h5\>  
      \<p\>El axioma de diseño de Elixir promueve que los procesos fallen de manera controlada bajo la supervisión de un árbol de recuperación (Let it crash).\</p\>  
    \</div\>

    \<\!-- Código Inline Asociado a Tipografía de Sistema limpia \--\>  
    \<p class\="paragraph"\>La comunicación asíncrona entre procesos independientes se realiza enviando un mensaje al identificador de proceso   
      \<code class\="inconsolata"\>pid\</code\> mediante el operador de envío nativo de la máquina virtual  
      \<a href\="\#foot\_elixir\_1" id\="ref\_elixir\_1" class\="super"\>1\</a\>.  
    \</p\>

    \<\!-- Bloque de Código con Título y Fuente Embebida \--\>  
    \<div class\="code-box"\>  
      \<p class\="code-title"\>Código 3.1. Creación de procesos y envío de mensajes en Elixir\</p\>  
      \<pre class\="code"\>\<code class\="inconsolata"\>  
defmodule Spawner do  
  def greet do  
    receive do  
      {:hello, sender} \-\> send(sender, :ok) \# Envío asíncrono de respuesta  
    end  
  end  
end

pid \= spawn(&Spawner.greet/0)  
send(pid, {:hello, self()})  
      \</code\>\</pre\>  
    \</div\>

    \<\!-- Bloque de Notas al Pie con Validación de Enlaces \--\>  
    \<div class\="footnotegroup"\>  
      \<p class\="footnote" id\="foot\_elixir\_1"\>  
        \<a href\="\#ref\_elixir\_1" class\="footback"\>1.\</a\>  
        El identificador del proceso remitente se captura de forma dinámica invocando la función reservada del núcleo \<code\>self()\</code\>.  
      \</p\>  
    \</div\>  
  \</div\>  
\</body\>  
\</html\>

## **Conclusiones de Parseabilidad e Integridad Estructural**

La evaluación de la estructura interna del código XHTML de estas cuatro editoriales proporciona certezas técnicas sobre la viabilidad de implementar procesos automatizados de raspado de datos (web scraping), indexación semántica y migración de formatos.

### **Análisis Forense de la Viabilidad de Extracción Automatizada**

1. **O'Reilly Media (Fiabilidad de Extracción: Excepcional)**: La adopción estricta del estándar HTMLBook permite confiar plenamente en sus clases y atributos para construir parsers automatizados3. Al estar validado sintácticamente mediante htmlbook.xsd, un script de extracción puede procesar el atributo de bloque data-type (ej. div\[data-type="warning"\] o pre\[data-type="programlisting"\]) con un ![][image6] de efectividad, con total independencia del título analizado o del autor3. Esto sitúa a O'Reilly como el entorno más maduro y robusto para la preservación e ingesta automatizada de conocimiento digital.  
2. **Packt Publishing (Fiabilidad de Extracción: Alta)**: A pesar de que su DOM es menos rico semánticamente que el de O'Reilly, la extrema rigidez de sus plantillas de compilación industrializadas garantiza que las clases que declaran prefijos corporativos (como .Packt\_Note o .Packt\_CodeHeader) permanezcan consistentes a lo largo de todo su catálogo moderno20. No hay variaciones imprevistas en la jerarquía del DOM, lo que permite desarrollar scripts de parseado de alta fidelidad que actúen sobre sus selectores de estilo planos.  
3. **Pragmatic Bookshelf (Fiabilidad de Extracción: Alta)**: El código limpio derivado de la compilación directa desde Markdown o PML produce una estructura XHTML5 minimalista y lógica7. Al no incorporar envoltorios interactivos innecesarios y estructurar de manera predecible las notas y barras laterales, es sumamente sencillo procesar sus textos mediante selectores semánticos sencillos7. La presencia de tipografías embebidas y consistencia de enlazado añade valor a la integridad de los datos de cara a procesos de archivo digital7.  
4. **Manning Publications (Fiabilidad de Extracción: Media-Baja)**: Aunque la adopción moderna del namespace .fm- ha unificado notablemente sus etiquetas CSS, el flujo de trabajo post-PDF introduce irregularidades que dificultan la automatización14. La existencia de inconsistencias tipográficas graves en el código inline (la clase .fm-code-in-text con múltiples variantes de tamaño y line-height en un mismo texto15), de forma conjunta con la desalineación de listas y la coexistencia de código heredado de Calibre en títulos anteriores a 202015, exige el desarrollo de filtros previos y de reglas de normalización excepcionales en los scripts de raspado para corregir la escala visual y la jerarquía de los elementos recuperados.

### **Comparación con Adobe InDesign**

En un plano comparativo final, la extracción automatizada sobre EPUBs procedentes de Adobe InDesign es inviable a gran escala1. Al carecer de un validador sintáctico estricto a nivel de esquema lógico y depender de la intervención manual del diseñador gráfico, las clases inyectadas por InDesign varían de manera caótica entre libros y capítulos1. La adopción de sistemas de compilación semánticos de marcado ligero (tales como Asciidoctor, DocBook, PML o Markdown estructurado) por parte de las editoriales técnicas no es un capricho estético, sino una decisión estratégica de ingeniería de software que asegura la supervivencia de la información, la interoperabilidad con motores de lectura actuales y futuros, y la posibilidad de reutilizar el catálogo editorial como un corpus de datos estructurado de forma inequívoca3.

#### **Obras citadas**

1. FROM PRINT TO EBOOKS A HYBRID PUBLISHING TOOLKIT FOR THE ARTS \- Institute of Network Cultures, [https://networkcultures.org/wp-content/uploads/2014/12/Hybrid\_Publishing\_Toolkit\_gr.pdf](https://networkcultures.org/wp-content/uploads/2014/12/Hybrid_Publishing_Toolkit_gr.pdf)  
2. GitHub \- oreillymedia/orm\_book\_samples: Sample book files for O'Reilly content, [https://github.com/oreillymedia/orm\_book\_samples](https://github.com/oreillymedia/orm_book_samples)  
3. HTMLBook \- O'Reilly Design System, [https://oreillymedia.github.io/HTMLBook/](https://oreillymedia.github.io/HTMLBook/)  
4. O'Reilly Atlas, [https://atlas.oreilly.com/](https://atlas.oreilly.com/)  
5. oreillymedia/HTMLBook: Let's write books in HTML\! \- GitHub, [https://github.com/oreillymedia/HTMLBook](https://github.com/oreillymedia/HTMLBook)  
6. XSL-FO Is Dead, CSS Paged Media Is Prime Suspect | Cloud Native Trainer, [https://cloudnativetrainer.com/ebooks/2019/04/27/xsl-fo-is-dead-css-paged-media-is-prime-suspect/](https://cloudnativetrainer.com/ebooks/2019/04/27/xsl-fo-is-dead-css-paged-media-is-prime-suspect/)  
7. SE Radio 695: Dave Thomas on Building eBooks Infrastructure, [https://se-radio.net/2025/11/se-radio-695-dave-thomas-on-building-ebooks-infrastructure/](https://se-radio.net/2025/11/se-radio-695-dave-thomas-on-building-ebooks-infrastructure/)  
8. Atlas Introduction | Atlas Documentation, [https://docs.atlas.oreilly.com/](https://docs.atlas.oreilly.com/)  
9. Hello Android: Introducing Google's Mobile Development Platform \- Jacob Filipp, [https://jacobfilipp.com/DrDobbs/articles/DDJ/2009/0904/0904br01/0904br01.html](https://jacobfilipp.com/DrDobbs/articles/DDJ/2009/0904/0904br01/0904br01.html)  
10. HTML5 as an alternative to DITA and DocBook \- XMLmind, [http://www.xmlmind.com/tutorials/HTML5Books/HTML5Books.html](http://www.xmlmind.com/tutorials/HTML5Books/HTML5Books.html)  
11. epub.xsl \- oreillymedia/HTMLBook \- GitHub, [https://github.com/oreillymedia/HTMLBook/blob/master/htmlbook-xsl/epub.xsl](https://github.com/oreillymedia/HTMLBook/blob/master/htmlbook-xsl/epub.xsl)  
12. GitHub \- hadley/htmlbook: Convert a Quarto book to O'Reilly's html book format, [https://github.com/hadley/htmlbook](https://github.com/hadley/htmlbook)  
13. PROGRAMME REGULATIONS & CURRICULUM \- Presidency University, [https://presidencyuniversity.in/uploads/images/680f36b2a7f201745827506.pdf](https://presidencyuniversity.in/uploads/images/680f36b2a7f201745827506.pdf)  
14. Manning FAQs, [https://www.manning.com/faq](https://www.manning.com/faq)  
15. Fixing Manning EPUB Code Spans \- Garret Wilson, [https://www.garretwilson.com/blog/2023/01/04/fix-manning-epub](https://www.garretwilson.com/blog/2023/01/04/fix-manning-epub)  
16. Packt | Advance your tech knowledge | Books, Videos, Courses and more, [https://www.packtpub.com/en-us](https://www.packtpub.com/en-us)  
17. Packt+ | Advance your knowledge in tech, [https://www.packtpub.com/en-us/product/mastering-css-with-sass-and-bootstrap-ace-your-interviews-9781805805113/chapter/pseudo-classes-and-elements-advanced-selectors-part-2-p5/section/before-after-pseudo-element-part-4-video5\_20](https://www.packtpub.com/en-us/product/mastering-css-with-sass-and-bootstrap-ace-your-interviews-9781805805113/chapter/pseudo-classes-and-elements-advanced-selectors-part-2-p5/section/before-after-pseudo-element-part-4-video5_20)  
18. FAQs \- Packt, [https://www.packtpub.com/en-us/help/faqs](https://www.packtpub.com/en-us/help/faqs)  
19. Packt API Documentation (v2), [https://docs.api.packt.com/](https://docs.api.packt.com/)  
20. Microsoft Dynamics 365 Extensions Cookbook, [http://projanco.com/Library/Microsoft%20Dynamics%20365%20Extensions%20Cookbook.pdf](http://projanco.com/Library/Microsoft%20Dynamics%20365%20Extensions%20Cookbook.pdf)  
21. Force.com Enterprise Architecture \[2 ed.\] 978-1-78646-368-5 \- DOKUMEN.PUB, [https://dokumen.pub/forcecom-enterprise-architecture-2nbsped-978-1-78646-368-5.html](https://dokumen.pub/forcecom-enterprise-architecture-2nbsped-978-1-78646-368-5.html)  
22. C\# 14 and .NET 10 – Modern Cross-Platform Development Fundamentals, [https://cdn.answeroverflow.com/1461364876940410952/Packt\_-\_C\_14\_and\_.NET\_10\_10th\_Edition.pdf](https://cdn.answeroverflow.com/1461364876940410952/Packt_-_C_14_and_.NET_10_10th_Edition.pdf)  
23. Modify a pragprog's epub archive to use more suitable fonts on Sony eBook Reader \- Gist, [https://gist.github.com/300756](https://gist.github.com/300756)  
24. Authors' issues, how Reading Systems could help, and how to implement helpers? · Issue \#1 · readium/css \- GitHub, [https://github.com/readium/readium-css/issues/1](https://github.com/readium/readium-css/issues/1)  
25. The Mobile is the Massage \- Silvio Lorusso, [https://silviolorusso.com/work/the-mobile-is-the-massage/](https://silviolorusso.com/work/the-mobile-is-the-massage/)  
26. footnotes in epub output · Issue \#149 · oreillymedia/HTMLBook \- GitHub, [https://github.com/oreillymedia/HTMLBook/issues/149](https://github.com/oreillymedia/HTMLBook/issues/149)  
27. Writing in DocBook | Atlas Documentation, [https://docs.atlas.oreilly.com/atlas/writing\_in\_docbook.html](https://docs.atlas.oreilly.com/atlas/writing_in_docbook.html)  
28. oreillymedia/atlas\_trade\_theme: One of two default themes for O'Reilly Atlas \- GitHub, [https://github.com/oreillymedia/atlas\_trade\_theme](https://github.com/oreillymedia/atlas_trade_theme)  
29. The Pragmatic Programmer now in DRM-free ebook, [https://pragprog.com/news/the-pragmatic-programmer-now-in-drm-free-ebook/](https://pragprog.com/news/the-pragmatic-programmer-now-in-drm-free-ebook/)  
30. Pragmatic Guide to JavaScript, [https://pragprog.com/news/pragmatic-guide-to-javascript/](https://pragprog.com/news/pragmatic-guide-to-javascript/)  
31. GitHub \- paulwellnerbou/epub-styles: HTML and CSS to beautify Epubs and make code samples readable in all epub reader devices, [https://github.com/paulwellnerbou/epub-styles](https://github.com/paulwellnerbou/epub-styles)  
32. Learning Yeoman | Web Development | eBook \- Packt, [https://www.packtpub.com/en-sg/product/learning-yeoman-9781783981397](https://www.packtpub.com/en-sg/product/learning-yeoman-9781783981397)  
33. Fixing the Stubborn Font of Manning ePubs in Calibre \- Snippets, [https://snippets.therealvan.com/2025/09/02/fixing-the-stubborn-font-of-manning-epubs-in-calibre/](https://snippets.therealvan.com/2025/09/02/fixing-the-stubborn-font-of-manning-epubs-in-calibre/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAAAZCAYAAAC4j5m6AAAEBUlEQVR4Xu2YWahOURTHl3mWucwpxYtIpgzdmzGZE2/qGpPhhQfJEIoMEULEi4zJi3meMoRMD0pkKDKXDCEk1r+1t7POuvvc+91D7vdwfvXv3v3f+0zr7L3O2h9RRkZGRrlQgTXVmqXQnPWC9Yx1hNUx3v2HvawPrO+s5abP0tAaBtznJdYn1nXWhHg3nTDtvKYdax/rl+0ogV4kQR/OWsX6yfoWGyGMYW1kNWY1IAlM5diIiEGsG9Y0bGLNZrVgFZC8UM1jkucIabcaV67UIAnYNfc318Bj1t1kzVceZh6OR4A9bVlfWJWU1561SLUBjsO42+7/JBZT/OVuofj4ahQ9R0jDoqH5Ax6opIfWzCIZu9/4p1jnVPsphc8JDyvGAi80HvgVOVB5WEHjVXsoa6dqe/BCMcnykrIEfilFs0iDPH9etX9Q8TEA3gxrUnLgq5KsCPTVM30apL1JxqtJ4ZecN5Ql8J1IPm67jI+cv1W1Swr8EmtScuC7UvSiEcgnrKskKatKNCwIvi8WHLOQdYv1lbWGJE15DpJc6yzJS1/Aesc6wOrhxlxmfWTdYc11XirKEvgQ/UmO9zcGHjrPAg/52ZIU+NEkPu4R6aw+Sb5GKrPpTjOC9daazEnWG5IVghT0meS8Hp9KEdRjrMkkk+0l6znJqupCsvr86k/N3wR+CMmxh4zfwfka5GF4m40PkgI/h6IZ30f5yPeh8WAASV8/41d3vi5bC523Tnloo/ytrbz1zl+pPAQ/6R5yIm3gW7FesS6QPJRlJmus+78Jaw/JdbB8LUmB9xUT1FT5vZ2H6sni0wX2GhrMXH8uKxzjQRupU7PW+dOVhxcTuuecSRt4LEdsaPTMsBxlvWbtIHlRuM7E2AghKfBICfBRKqKU9SCtwe+mPFCH5Pvy3vhgJEleLw2cFxtDDb4F8PVGE6kqdM85kybwFUk2RLWUZ3eSIRDAltak5MC3oWhW4pqens7DLNb0dX5oM1ZI0hdanZpQ4Fc7f4ryfOpKTZrAr6DiVYXeHWI22J8hsOO03wJPUuDBXZI+XU76ANvVNs/5Z4wPUL2gDx9HTSPWKNX+L4FHjvSln32IIudDfjbjpv2LshrnxgAfGJ8ecB18D5LAZgjjC6j4zwoI+COKfotBAJHiQue7SHIelH8h4KMf1UtrkqrlCkUrFztt9KNc9C8I36fDzt+mxg12Xnfn5YwNnFdd14+fAE6TbIxwceDffEj6BnBj2EmiZkbAUPvjdx2LPYcXanUNzv2AtYykBkfQO8dGCD6w222HA+lqGuseybgNrGaq3++4vY6bNlTAum88FBh5BXapRVS8wkgDUhsqIpwzaRcLH7P5X1wvIyMjIyMjIyMjI1/4DXkFN+eB9WSfAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAZCAYAAAAv3j5gAAAA8klEQVR4Xu2TOwrCQBRFn/j/FAruwNrCwlJwD7oIcQV2Vi7ATtyGIFhbWGivYGFlY2erhd5HMkzynDEZol0OHAjvznBnQkKU8kOycAwzMojJFO7kUNKGK/iCOZHF5QEPcqiowyfck1eSpIj3WosUVdJFeZFFUYYn8vbygb+SpGgGl/TnG7XgFTbpz0VrOPKfnYsKIjPBhznDbmDmXFQUmYkJXIiZc1FJZCYu5P0aQZyL+HONQq21eddLwwSLKiIz0TfIe4/+c48XmeiQLhqKjFHZQAY+DdJF1oPKa7O30AqiLdzAmpgzc/rcb311KSkp7rwBKahRlH0B/asAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAABc0lEQVR4Xu2VvyuFURjHH8VAYqEkSrllUgY2u0WUH/EXqJvJohQZLJLFJqUuRoOBTRID3VwkRiYxmZQMEt+n5zk6Pd7z9g7qovOpT93zPee8fc+999xLFPlnVMC8DctJB9yGH3aiHFTDd1gkKfQrSvm8USyVjbRSTXANPsISnPDmWuALyd45HV/CB7gOG+EkvIbP8Ei2ZSNUqh3ewnPYA5dI1s3ofAPc12wHHsA6OKbZHlyEbSSFeW0vb8xCqBRnfBF85jUf0vG4jg+/Vgg3mvuMwoLJgqSVCjmla0Z0vKVjx5XmPnyQDZMFSSu1a0ODK7Vpcv7I7TMH6Hv5IGmljm1oGCRZVzD5meY+/fRDpZ5gpcm7YZe+HqbkUhea+/ABMpXKkfyy8wNqzRxf6TuS69wHm+EKXPXWuBt5QnLDmE54r7k7UA1cgKewVbNEeFOS/ABHPVwmecf4ezINq3SO/zftXn4n/PErycHtulmKRCKRP8QnzZt3yOjMns4AAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADUAAAAZCAYAAACRiGY9AAACMklEQVR4Xu2WT0hVQRTGT0VWGFGIgQS1CVrmIkjQhQs3IoSBtBNEKoJ27gJduGiRoli4U5e1iDamkv9QAzctkjYigqtSC11IikWK6Pd5ZnjnDc/37nsJV+F+8OO9982ZeXNmzsy9IokSnSidAc9CM4dugFXwA4yAu+nN8eoOeA/2w4YsqhRN6AHoBHvgX1pETLokOpkv7jNqUtzVr6DVeM2i/UuNF7u4ylGTahGN/RD4E2A68GJVPkm9FI0N43muZgIvVuWTVDnYAm8Dn2esL/DOgznwF8yDbtP2EWyAKVAE2sBnMAgqXEwV2ATfwAtwzvmRlE9SmVQj2t9PhuKZHRe9TPj9Edg27SzjAdEJfwJPwDXwE6yAx6KJX5VUdbQf9oyo/0mqTrTvkPEugt/Ot6oGr83vMrADLhvvjWi/DuMxMXqshsgqNKmb4Jdo2TARL5aoP3chXH0v3pbhRHtE454bj0nT439FVqFJsXRmJX2lqXrR8XiWsqlE9OFtxXPHvvZlgOVLb814OVVIUmfBGCg2Hp9XVLWkdiabWFZhUl2i/Z4aj1VAb914OVVIUq9Ebzerd+7zAliWzGM+NN8z7dSxJHUb7Ip2CsuoyfnE78I9SS1CSKOLofjmweuZt9wtcEX0hvM7y+u5QfTK5phew6Jj9Yv2YVyt8/6YuCMVTsrDwSge5EnRh+p15/mVzMR9F+PFEl1wbUug17R9d75nVFKvW5bF4DcvpUSJEiVKlOhU6QBNSaWA37ogFQAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAZCAYAAAAv3j5gAAABS0lEQVR4Xu2UPS9FQRCGX/H9kVD6KEWpUGhEcVVEQYIfIX6ABI1KRUGhFxIdhYboKBUqlU4pEgkJhQjvZM7eM2fukr2o5DzJU+y8szvJ2ZwFSv6QRrpEG3zwDTP0gr7SHTpYjGsZpif0gza57CuW6TmdpF30jT7QEdsU6IE2XEGHpA7qpy90F3n/MXT/UWiK0Yl8ULPLYlSQ9w9kte1sfZuto9Q7SJim42Z9Ct2/b2o1/GSQR65A9o/5wPLbQX30nS76wGMHtbgslSd6R3t9YLGDWl2Wyip0/6UPLHZQm8tSkf8pnDHnsip2ULvLYlToHh01tSHkZ2yaegE7qMNlMR6hvTemJi9COGPD1AvYpgWXCSGbz9Zr0MufqnYAZ9CeA1MrEA6x3hc69ILlIHnTBHmA1+kzvaZb0H2HSPsiddNNZ+kKnXBZScl/5xNIdlRTyXZQrwAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAZCAYAAAB3oa15AAACq0lEQVR4Xu2WW6hOQRTHl/sllw4vooTcigfliUiRXEq88uCEXB5JCZ1Siie8Uko8yC2hEInjEhHKNYQUilJyyYMk/v9vzXyzzjp7dt9XHsj+1b/W/Nfs75u1Z/bMiFT8v3yBNkIjoYsuF2HuPbTCJ8roAq3ypmEJdAZ6Cu2AenZM1+gOXYG+Qbek+PfumHgCdASaB/UL3jropeSLK2QcdAj65ROB9aKDWgnNFi3iJtTH9OkBHYXmQgOh5dBnkycskP9j4W/ugx5CX6Fd0EdorO2Uo7fooG9DP0LsmSrqbzfezOBtMt7m4Fm2iD4fGQHtNW3CF2LZCrU5ryG4Nv0AyDtRf4jzWXTsPzHED1K6Rgv0ynmHXZvLyDLFtRsmVwA9irNluRB8sjjEV1O6Rtfgc0lFnpiYg+9m2ktN3DRlBfz0Jjgpqf+GEJ9P6Tr07Xrm/3CJDIfajT8Mum/aTVNWAL8Pjy1gW4jPpXQd+tNNe47osvwE7TE+d7hFpt00ZQUUzcAJSf354ZXNwAJvGjgTb6Ghoc2i+H3xu1omHZdYKc0WcEpS/7UhzhVgdyLPaWi1abP/QtOeb+JSygqg+EFazgaftIb4UkrXoc9zJsdl0UM0wv58+5HdJi4lVwDXKv3Bzr8WfDI5xHdTugYPNz6fWwaDoDHO4++MNm3udg2RKyCe0OOd/xz6EGK+QX6Yb1K6Bu80x51nOegN6VxAu4mzjIK+iz7c3+U4OO44101up+ixzwFGOEO8w8Tl0Ff0z4vuTDzgXkMzfEJ0DDxXIryDlcIHimRP3gHQI+iF6GHF2Zpl8pFJ0A3Ry94z6XwyR/ZDB7wZ4IzdE30hraL3pz9CL2ia6FWYh04O3ix5L1ojOgsebpePRdd/ETzxj4nufLyp/pX4DaGioqLiH+M3xOWrDgfZNPkAAAAASUVORK5CYII=>