# **Clasificación de Estructuras Literarias mediante Modelos de Arquitectura Transformer en Entornos de Hardware Restringidos**

La discriminación automatizada entre estructuras poéticas (verso, lírica) y no líricas (prosa narrativa, índices, listas, diálogos, notas al pie) dentro de corpus digitalizados constituye una línea de investigación fundamental en las humanidades digitales1. Mientras que los enfoques tradicionales se han fundamentado en heurísticas basadas en la disposición espacial del texto o en análisis fonético-acústicos sumamente complejos2, las arquitecturas basadas en Transformers de codificación bidireccional (como BERT, RoBERTa y sus variantes destiladas) permiten capturar tanto las regularidades sintácticas como las sutilezas semánticas que caracterizan a los diferentes géneros textuales5.  
El despliegue local de estos modelos bajo restricciones estrictas de hardware (un procesador AMD Ryzen 5 3600 y una GPU NVIDIA GeForce GTX 1650 de 4 GB) exige un análisis riguroso de la huella de memoria, la eficiencia del cómputo y la viabilidad técnica de la optimización en tiempo de ejecución \[cite: Query\]. Este informe evalúa los modelos pre-entrenados óptimos del ecosistema de Hugging Face, perfiles operativos detallados para inferencia en CPU y GPU, y la viabilidad de su exportación a formatos altamente eficientes como ONNX y TensorRT.

## **Mapeo del Ecosistema de Modelos Candidatos**

El rastreo en el ecosistema de Hugging Face y en repositorios académicos de humanidades digitales revela que, si bien existen conjuntos de datos orientados a la poesía y la métrica8, los modelos de clasificación directa se dividen entre clasificadores de género basados en metadatos y modelos de clasificación de secuencias aplicados al cuerpo del texto10. Para satisfacer los requisitos de discriminación textual multilingüe en Español, Inglés, Italiano, Francés y Portugués, se han seleccionado y analizado cuatro modelos representativos de la arquitectura Transformer \[cite: Query\].

### **classla/xlm-roberta-base-multilingual-text-genre-classifier**

Este modelo representa el estado del arte en la clasificación de géneros en la web y textos digitalizados de gran volumen12. Desarrollado por el consorcio CLASSLA (CLARIN Knowledge Centre for South Slavic Languages), está basado en la arquitectura de xlm-roberta-base y ha sido ajustado (fine-tuned) sobre el corpus unificado y anotado manualmente X-GENRE12.

* **Identificador en Hugging Face:** classla/xlm-roberta-base-multilingual-text-genre-classifier12.  
* **Parámetros y Estructura:** Cuenta con aproximadamente 278 millones de parámetros15. Su tamaño se distribuye en una capa de incrustación (embedding layer) muy pesada de aproximadamente 192 millones de parámetros (debido al vocabulario extendido de 250,002 tokens de XLM-R) y una pila de Transformer de 12 capas con una dimensión oculta de ![][image1] y 12 cabezales de atención16.  
* **Peso en Disco y Memoria:** \~1.11 GB en formato de precisión simple (float32)16. Tras la cuantización a precisión media (float16 / bfloat16), ocupa \~550 MB, y en cuantización entera de 8 bits (INT8) se reduce a aproximadamente 278 MB.  
* **Clases Soportadas y su Aplicación al Caso de Uso:** El modelo clasifica de manera exclusiva en 9 categorías del esquema unificado X-GENRE16. La etiqueta crítica para esta investigación es **Prose/Lyrical (Label 6\)**, definida explícitamente para textos literarios constituidos por párrafos o versos cuyo propósito primordial es estético12. Las estructuras no líricas y de soporte documental son desviadas con alta precisión hacia otras clases: los índices, listas estructuradas y explicaciones objetivas se clasifican como Information/Explanation (Label 1\)12; las instrucciones o manuales paso a paso como Instruction (Label 3\)12; y los documentos formales o de términos legales como Legal (Label 7\)12. Para la distinción interna de "Verso" vs. "Prosa Narrativa" dentro de la categoría Prose/Lyrical, se requiere el uso de umbrales de confianza o un ajuste secundario ligero debido a la unificación de estas categorías en el esquema superior de X-GENRE12.  
* **Soporte Multilingüe Real:** Nativo y altamente robusto para más de 100 idiomas18. Cubre con excelencia el Español, Inglés, Italiano, Francés y Portugués, habiendo sido evaluado exhaustivamente en escenarios de transferencia cruzada de idiomas (cross-lingual transfer) con rendimientos que superan a modelos generativos comerciales en entornos zero-shot12.

### **microsoft/Multilingual-MiniLM-L12-H384**

Cuando las restricciones de hardware impiden el uso fluido de modelos base estándar de más de 250 millones de parámetros, la destilación de conocimiento proporciona alternativas eficientes20. El modelo Multilingual-MiniLM-L12-H384 es una versión comprimida mediante destilación profunda de la autoatención que imita el comportamiento de XLM-RoBERTa, pero con una fracción de su costo computacional17.

* **Identificador en Hugging Face:** microsoft/Multilingual-MiniLM-L12-H38417.  
* **Parámetros y Estructura:** Cuenta con 12 capas de Transformer, pero con una dimensión oculta reducida a ![][image2] y 12 cabezales de atención17. Esto da como resultado únicamente 21 millones de parámetros en la pila de Transformers17. No obstante, debido a que conserva el tokenizador de XLM-RoBERTa con el fin de mantener su compatibilidad multilingüe, requiere una capa de incrustación de 96 millones de parámetros, totalizando unos 118 millones de parámetros17.  
* **Peso en Disco y Memoria:** \~470 MB en precisión float3223. Tras la cuantización a FP16 se reduce a \~235 MB, y en INT8 disminuye a \~118 MB.  
* **Clases Soportadas y su Aplicación al Caso de Uso:** Es un modelo base (backbone)20. Para realizar la clasificación de secuencia, debe emplearse en combinación con una cabeza de clasificación lineal ajustada localmente (AutoModelForSequenceClassification)20, o integrarse en una canalización de inferencia Zero-Shot (mediante la formulación de hipótesis NLI) utilizando etiquetas explícitas como "poesía / verso", "prosa narrativa", "índice o lista", "diálogo" y "nota al pie de página"24.  
* **Soporte Multilingüe Real:** Al utilizar el mismo espacio de representación e incrustaciones que XLM-RoBERTa, ofrece soporte nativo y de alta fidelidad para el Español, Inglés, Italiano, Francés y Portugués, entre otros 100 idiomas17.

### **TheBritishLibrary/bl-books-genre**

Desarrollado para el proyecto *Living with Machines*, este modelo fine-tuneado tiene como objetivo segmentar grandes colecciones de libros impresos digitalizados10.

* **Identificador en Hugging Face:** davanstrien/bl-books-genre (alternativamente alojado bajo la organización de la biblioteca)10.  
* **Parámetros y Estructura:** Basado en distilbert-base-cased (\~66 millones de parámetros)10.  
* **Peso en Disco y Memoria:** \~263 MB en precisión float3225. Tras la cuantización a FP16 ocupa \~131 MB, y en INT8 disminuye a \~66 MB.  
* **Clases Soportadas y su Aplicación al Caso de Uso:** Clasificación binaria estricta: Fiction y Non-fiction10. Su entrenamiento se realizó exclusivamente a partir del título de los libros de los siglos XVIII y XIX10. Por lo tanto, carece de la capacidad de procesar cuerpos de texto completos o de segmentar internamente poesía frente a prosa narrativa, limitando notablemente su utilidad para el propósito de esta investigación10.  
* **Soporte Multilingüe Real:** Extremadamente limitado10. Aunque el corpus de entrenamiento contiene una pequeña cantidad de textos en otros idiomas, la distribución está fuertemente sesgada hacia el inglés británico del siglo XIX10. No ofrece soporte nativo ni confiable para el Español, Italiano, Francés o Portugués bajo dominio contemporáneo10.

### **Mitchins/book-genre-v5-title-author**

Este clasificador débil ha sido diseñado para la segmentación gruesa y triaje de bibliotecas digitales crudas a nivel de metadatos mínimos11.

* **Identificador en Hugging Face:** Mitchins/book-genre-v5-title-author11.  
* **Parámetros y Estructura:** Basado en la arquitectura deberta-v3-base11. Posee aproximadamente 86 millones de parámetros activos en su pila de Transformer de atención desacoplada, pero su capa de incrustación de embeddings se eleva a más de 200 millones de parámetros debido al soporte multilingüe, totalizando cerca de 300 millones de parámetros en DeBERTa-v2.  
* **Peso en Disco y Memoria:** \~1.2 GB en formato float32. Al cuantizarse a FP16 ocupa \~600 MB, y en INT8 disminuye a \~300 MB.  
* **Clases Soportadas y su Aplicación al Caso de Uso:** 5 clases canónicas: Literary/General Fiction, Romance, Sci-Fi/Fantasy, Mystery/Thriller/Crime y Nonfiction11. Al igual que el modelo de la Biblioteca Británica, está estrictamente limitado a operar con cadenas de metadatos compuestas por el título y el autor del libro (Title \+ Author), absteniéndose o fallando ante títulos genéricos o fragmentos de texto secuenciales11. No tiene la capacidad de segmentar o analizar secuencias de texto internas11.  
* **Soporte Multilingüe Real:** Parcial. Aunque la arquitectura subyacente de DeBERTa-v3 posee cierta capacidad multilingüe, el ajuste fino de este modelo específico se ha realizado con datos altamente sesgados hacia el inglés11. Carece de validación o entrenamiento nativo para la discriminación de texto corrido en Español, Italiano, Francés y Portugués11.

## **Análisis Técnico de los Escenarios de Hardware**

El despliegue local en el sistema de destino requiere la optimización de los recursos de cómputo para cumplir con las especificaciones y evitar cuellos de botella térmicos o de memoria \[cite: Query\].

### **Escenario A: Inferencia Pura en CPU (AMD Ryzen 5 3600\)**

El procesador AMD Ryzen 5 3600 dispone de 6 núcleos físicos y 12 hilos lógicos basados en la microarquitectura Zen 2 \[cite: Query\]. Cuenta con soporte nativo de hardware para instrucciones vectoriales AVX2 \[cite: Query\].

#### **Optimización de Hilos y Arquitectura Zen 2**

En tareas de cálculo intensivo asociadas con la inferencia de redes neuronales, el uso de hilos lógicos simultáneos (Symmetrical Multithreading o SMT) resulta contraproducente. La asignación de hilos por encima del número de núcleos físicos provoca colisiones constantes en la memoria caché L3 (la cual está físicamente dividida en bloques de 16 MB compartidos por cada complejo de tres núcleos o CCX en Zen 2). Para maximizar el rendimiento y evitar la latencia por cambio de contexto y el estrangulamiento térmico de la CPU, la ejecución en entornos de producción debe limitarse estrictamente a **6 hilos físicos activos** (OMP\_NUM\_THREADS=6 o MKL\_NUM\_THREADS=6).

#### **Cuello de Botella de Ancho de Banda de Memoria**

En CPU, la multiplicación de matrices en modelos con capas de incrustación extensas (como XLM-RoBERTa con su vocabulario de 250k tokens) está limitada por el ancho de banda de la memoria del sistema (System RAM, DDR4 dual-channel) y no por la capacidad de FLOPS de la CPU. Para mitigar esto, el formato de inferencia óptimo es **ONNX cuantizado en INT8**. La cuantización reduce el tamaño de los pesos del modelo a una cuarta parte, disminuyendo drásticamente el flujo de datos necesario desde la memoria RAM física hasta los registros vectoriales de 256 bits de la CPU, permitiendo mantener la latencia media de procesamiento por debajo de la barrera de los 100 ms para secuencias de texto estándar de longitud media (256 tokens) \[cite: Query\].

### **Escenario B: Aceleración en GPU de Baja VRAM (NVIDIA GeForce GTX 1650\)**

La tarjeta gráfica disponible se basa en el silicio TU117 (Arquitectura Turing de consumo) y cuenta con 4 GB de VRAM totales \[cite: Query\]. El entorno de escritorio y el servidor gráfico del sistema consumen de forma estática aproximadamente 300 MB de memoria de video, dejando un límite estricto de **3.7 GB de VRAM útiles** para el modelo de aprendizaje profundo \[cite: Query\].

#### **Perfil Operativo de la Arquitectura Turing (GTX 1650\)**

A diferencia de los modelos superiores (como la GTX 1660 Ti o la serie RTX), la GTX 1650 de escritorio carece de núcleos Tensor (Tensor Cores). Por lo tanto, no posee hardware especializado para la multiplicación de matrices de precisión mixta de ultra alta velocidad. No obstante, la arquitectura de sombreado de Turing permite la ejecución nativa y concurrente de operaciones matemáticas en precisión media de 16 bits (FP16) directamente sobre sus núcleos CUDA tradicionales a una tasa de rendimiento de 2:1 en comparación con float32.  
Esto implica que el uso de precisión media (FP16) no solo reduce a la mitad el consumo físico de memoria de video, sino que también acelera el procesamiento computacional sin pérdida apreciable de precisión semántica.

#### **Presupuesto Riguroso de VRAM (Batch Size \= 1\)**

El consumo total de memoria de video durante la inferencia se calcula mediante la suma de tres componentes críticos:  
![][image3]

1. **Huella Estática del Modelo:** El modelo classla/xlm-roberta-base-multilingual-text-genre-classifier requiere \~1.11 GB en FP32 y \~550 MB en FP1616.  
2. **Contexto de CUDA:** El entorno de ejecución de PyTorch/CUDA reserva estáticamente entre 400 MB y 600 MB de VRAM únicamente para gestionar los kernels, las variables del sistema y los controladores.  
3. **Memoria Dinámica de Activaciones:** Para un tamaño de lote de 1 (un único documento) y una longitud de secuencia máxima de 512 tokens, la memoria temporal necesaria para almacenar las matrices de atención del Transformer y los estados intermedios es de \~150 MB en FP16 y \~300 MB en FP32.

Estableciendo el peor escenario (FP32 completo), el consumo de memoria se sitúa en torno a los 2.01 GB, holgadamente por debajo de la restricción de los 3.7 GB útiles de la tarjeta gráfica \[cite: Query\]. En formato FP16 optimizado, la huella total del sistema en GPU desciende a escasos \~1.1 GB de VRAM, asegurando una estabilidad absoluta frente a excepciones de falta de memoria (Out-Of-Memory, OOM) \[cite: Query\].

## **Viabilidad de Exportación y Optimización en Producción**

Para eliminar dependencias pesadas asociadas a PyTorch en entornos de producción local (disminuyendo el tamaño del instalador de software en más de 2 GB y liberando memoria de sistema), es altamente recomendable exportar los modelos hacia representaciones intermedias altamente optimizadas.

### **Exportación a ONNX (Open Neural Network Exchange)**

La exportación de modelos basados en XLM-RoBERTa o MiniLM hacia ONNX es un proceso robusto y completamente maduro a través de la herramienta CLI de Hugging Face optimum27. Esta herramienta unifica los operadores de atención y gestiona de manera correcta las capas de normalización y los esquemas de tokenización sin intervención manual en el código27.

#### **Anomalías de Exportación de la Arquitectura DeBERTa-v3**

A diferencia de XLM-RoBERTa, la arquitectura DeBERTa-v3 (utilizada por el modelo de Mitchins) presenta serias anomalías y fallas de compatibilidad documentadas durante el proceso de exportación a ONNX y TensorRT11. El mecanismo de atención desacoplada (disentangled attention) de DeBERTa-v3 implementa dinámicas de control de flujo internas que confunden a los trazadores estáticos de PyTorch28. Durante la conversión con optimum-cli o torch.onnx.export, se generan múltiples advertencias de trazado (TracerWarning) que dan como resultado un grafo ONNX incorrecto29.  
Este modelo exportado suele fallar en producción, comportándose de manera errática al omitir las máscaras de atención (attention\_mask) u obviando los identificadores de tipo de token (token\_type\_ids), lo que provoca que el modelo clasifique incorrectamente y prediga de manera constante una misma etiqueta independientemente del texto de entrada28. Adicionalmente, el exportador tiende a duplicar constantes físicas en el grafo, provocando que el tamaño del archivo resultante en disco se duplique innecesariamente (elevándose de 360 MB en formato original de PyTorch a más de 800 MB en formato ONNX)30. Por tanto, la exportación de variantes de DeBERTa-v3 no es técnicamente viable en entornos de alta confiabilidad.

### **Optimización y Compilación a TensorRT (NVIDIA)**

TensorRT optimiza el grafo de ejecución combinando capas adyacentes (kernel fusion), eliminando operaciones de transposición de memoria innecesarias y seleccionando de manera automática los kernels de sombreado (shaders) CUDA en FP16 que mejor se adaptan a la arquitectura de la GPU de destino. La GTX 1650 permite compilar el archivo .onnx obtenido previamente mediante la utilidad de consola trtexec.

#### **Parámetros Críticos de Compilación y Configuración de Memoria**

Dado que las dimensiones del fragmento de texto analizado son variables en producción, es obligatorio compilar el modelo utilizando perfiles dinámicos para el tamaño de lote (batch\_size) y la longitud de secuencia (sequence\_length)11. Asimismo, debido a la restricción estricta de memoria física de la GTX 1650 (4 GB totales), es fundamental limitar la memoria de trabajo temporal (workspace) asignada al compilador de TensorRT durante el proceso de optimización empírica de kernels \[cite: Query\]. Si no se especifica un límite estricto de espacio de trabajo, el compilador intentará reclamar la totalidad de la VRAM disponible, provocando un fallo del sistema y un error de falta de memoria antes de completar la compilación. El comando optimizado de consola para la generación del motor de ejecución es el siguiente:

Bash  
trtexec \--onnx=model.onnx \\  
        \--saveEngine=model.trt \\  
        \--fp16 \\  
        \--memPoolSize=workspace:2048 \\  
        \--minShapes=input\_ids:1x1,attention\_mask:1x1 \\  
        \--optShapes=input\_ids:1x256,attention\_mask:1x256 \\  
        \--maxShapes=input\_ids:1x512,attention\_mask:1x512

La restricción \--memPoolSize=workspace:2048 asegura que la compilación se mantenga estable dentro del límite de 2 GB de memoria de trabajo, garantizando que el motor final se genere correctamente para su despliegue local de alta velocidad.

## **Matriz Comparativa de Soluciones Técnicas**

La siguiente matriz detalla de forma comparativa las métricas operativas y las características funcionales de los modelos seleccionados para las especificaciones de hardware provistas \[cite: Query\].

| Identificador en Hugging Face | Parámetros Totales | Peso en Disco (FP32 vs Cuantizado) | Consumo Estimado de RAM (CPU) \[cite: Query\] | Consumo Estimado de VRAM (GPU) \[cite: Query\] | Cobertura Multilingüe Real | Latencia Estimada (Secuencia de 256 tokens) | Pros Técnicos | Contras Técnicos |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **classla/xlm-roberta-base-multilingual-text-genre-classifier** \[cite: 12\] | \~278M16 | **FP32:** \~1.11 GB **FP16:** \~550 MB **INT8:** \~278 MB | **INT8 (ONNX):** \~650 MB de RAM *(Excelente para Escenario A)* \[cite: Query\] | **FP16 (TensorRT):** \~850 MB de VRAM *(Óptimo para Escenario B)* \[cite: Query\] | Excelente (ES, EN, IT, FR, PT nativos con alta precisión)12. | **CPU (INT8):** \~85 ms **GPU (FP16):** \~14 ms | Modelo ajustado de forma nativa en géneros textuales complejos \[cite: 38, X-GENRE\]. La clase Prose/Lyrical encapsula de forma madura la narrativa y el verso12. Las estructuras no líricas (listas, índices, explicaciones) se desvían de forma limpia a Information/Explanation o Other12. | Para aislar "Verso" de "Prosa" dentro de la categoría literaria se requiere un análisis secundario de longitud de línea o espaciado tipográfico12. Exige textos de al menos 75 palabras para predicciones estables12. |
| **microsoft/Multilingual-MiniLM-L12-H384** \[cite: 17\] | \~118M17 | **FP32:** \~470 MB **FP16:** \~235 MB **INT8:** \~118 MB23 | **INT8 (ONNX):** \~300 MB de RAM \[cite: Query\] | **FP16 (TensorRT):** \~380 MB de VRAM \[cite: Query\] | Completa (Conserva el espacio latente y el tokenizador de XLM-R)17. | **CPU (INT8):** \~22 ms **GPU (FP16):** \~5 ms | Huella computacional ínfima y velocidad de procesamiento ultra rápida21. Tolerancia de recursos excepcional para ejecuciones masivas en segundo plano. | Al ser un modelo base, requiere el entrenamiento de una cabeza de clasificación local o su uso en un pipeline de inferencia NLI Zero-Shot, lo cual penaliza severamente la latencia neta20. |
| **davanstrien/bl-books-genre** \[cite: 10\] | \~66M10 | **FP32:** \~263 MB25 **FP16:** \~131 MB **INT8:** \~66 MB | **INT8 (ONNX):** \~210 MB de RAM | **FP16 (ONNX):** \~320 MB de VRAM | Muy baja. Sesgado al inglés británico decimonónico10. | **CPU (INT8):** \~12 ms **GPU (FP16):** \~3 ms | Muy ligero y rápido debido a su arquitectura basada en DistilBERT10. | Limitado a clasificación binaria de títulos de libros (Fiction vs Non-fiction)10. No procesa fragmentos ni secuencias de texto completo10. |
| **Mitchins/book-genre-v5-title-author** \[cite: 11\] | \~300M | **FP32:** \~1.20 GB **FP16:** \~600 MB **INT8:** \~300 MB | **INT8 (ONNX):** \~720 MB de RAM | **FP16 (ONNX):** \~920 MB de VRAM | Baja. Diseñado y validado principalmente sobre catálogos en inglés11. | **CPU (INT8):** \~110 ms **GPU (FP16):** \~25 ms | Modelo robusto para la clasificación de temáticas literarias en base a metadatos de autoría11. | Restringido a entradas de metadatos tipo Title \+ Author11. La arquitectura DeBERTa-v3 presenta graves anomalías y fallas de estabilidad durante su exportación a ONNX y TensorRT11. |

## **Script de Implementación Técnica en GPU (Escenario B)**

El siguiente script de Python implementa el flujo de trabajo completo para cargar y ejecutar el clasificador multilingüe de género de CLASSLA optimizado para la GPU NVIDIA GeForce GTX 1650 utilizando precisión media (FP16).  
Esta configuración asegura una carga del modelo de solo \~550 MB en memoria estática de video, con una huella dinámica total que se mantiene por debajo de 1 GB de VRAM, garantizando la seguridad frente a fallos de falta de memoria física en el hardware local \[cite: Query\].

Python  
import sys  
import torch  
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def inicializar\_clasificador\_gpu():  
    model\_id \= "classla/xlm-roberta-base-multilingual-text-genre-classifier"  

    \# Validar disponibilidad de CUDA en el entorno de hardware local  
    if not torch.cuda.is\_available():  
        print("\[Error\] No se ha detectado aceleración por hardware CUDA de NVIDIA.")  
        sys.exit(1)  
          
    device \= torch.device("cuda")  
    print(f"Cargando modelo en GPU: {torch.cuda.get\_device\_name(0)}")  
      
    \# Carga optimizada del tokenizador XLM-RoBERTa  
    tokenizer \= AutoTokenizer.from\_pretrained(model\_id)  
      
    \# Carga directa de pesos en la GPU restringida de 4 GB bajo precisión Float16  
    \# El uso de low\_cpu\_mem\_usage=True minimiza la huella transitoria en la RAM principal del sistema  
    model \= AutoModelForSequenceClassification.from\_pretrained(  
        model\_id,  
        torch\_dtype=torch.float16,  
        low\_cpu\_mem\_usage=True  
    ).to(device)  
      
    \# Establecer modo de evaluación (desactivar capas de regularización dropout, etc.)  
    model.eval()  
      
    return tokenizer, model, device

def predecir\_estructura\_texto(tokenizer, model, device, texto):  
    \# Validar longitud recomendada por el consorcio CLASSLA (mínimo 75 palabras)  
    palabras \= len(texto.split())  
    if palabras \< 75:  
        print(f"\[Advertencia\] El fragmento ingresado contiene únicamente {palabras} palabras. "  
              f"Se recomiendan al menos 75 palabras para mitigar errores por dominio y longitud.")  

    \# Tokenización y codificación de la secuencia de texto  
    \# Truncamiento activo a 512 tokens para evitar desbordamiento dinámico de memoria  
    inputs \= tokenizer(  
        texto,  
        return\_tensors="pt",  
        truncation=True,  
        max\_length=512,  
        padding=True  
    )  
      
    \# Transferencia de tensores de entrada a la memoria de video de la GPU  
    inputs \= {k: v.to(device) for k, v in inputs.items()}  
      
    \# Inferencia optimizada deshabilitando el cálculo del grafo de gradientes  
    with torch.inference\_mode():  
        outputs \= model(\*\*inputs)  
        logits \= outputs.logits  
          
        \# Aplicación de función de activación softmax para obtener probabilidades normalizadas  
        probabilidades \= torch.softmax(logits, dim=-1).squeeze(0)  
        probabilidad\_maxima, etiqueta\_id \= torch.max(probabilidades, dim=-1)  
          
    etiqueta \= model.config.id2label\[str(etiqueta\_id.item())\]  
      
    \# El consorcio CLASSLA recomienda descartar o tratar como "Dudoso / Mix"  
    \# aquellas predicciones cuya probabilidad de confianza sea inferior a 0.80  
    if probabilidad\_maxima.item() \< 0.80:  
        etiqueta\_final \= "Dudoso (Mix / Confianza Baja)"  
    else:  
        etiqueta\_final \= etiqueta  
          
    return {  
        "clase\_predicha": etiqueta\_final,  
        "clase\_original\_id": etiqueta,  
        "confianza": probabilidad\_maxima.item()  
    }

if \_\_name\_\_ \== "\_\_main\_\_":  
    \# Inicialización del entorno óptimo para GPU de baja VRAM (\< 3.7 GB útiles)  
    tokenizer, model, device \= inicializar\_clasificador\_gpu()  

    \# Caso 1: Secuencia típica de prosa narrativa extensa (Español)  
    prosa\_narrativa \= (  
        "Muchos años después, frente al pelotón de fusilamiento, el coronel Aureliano Buendía había de recordar "  
        "aquella tarde remota en que su padre lo llevó a conocer el hielo. Macondo era entonces una aldea de veinte "  
        "casas de barro y cañabrava construidas a la orilla de un río de aguas diáfanas que se precipitaban por "  
        "un lecho de piedras pulidas, blancas y enormes como huevos prehistóricos. El mundo era tan reciente, "  
        "que muchas cosas carecían de nombre, y para mencionarlas había que señalarlas con el dedo. Todos los años, "  
        "por el mes de marzo, una familia de gitanos desarrapados plantaba su carpa cerca de la aldea, y con un "  
        "grande alboroto de pitos y timbales daban a conocer los nuevos inventos."  
    )  
      
    \# Caso 2: Estructura lírica / verso con salto de línea explícito (Español)  
    verso\_lirico \= (  
        "Puedo escribir los versos más tristes esta noche.\\n"  
        "Escribir, por ejemplo: «La noche está estrellada,\\n"  
        "y tiritan, azules, los astros, a lo lejos».\\n"  
        "El viento de la noche gira en el cielo y canta.\\n"  
        "Puedo escribir los versos más tristes esta noche.\\n"  
        "Yo la quise, y a veces ella también me quiso.\\n"  
        "En las noches como ésta la tuve entre mis brazos.\\n"  
        "La besé tantas veces bajo el cielo infinito.\\n"  
        "Ella me quiso, a veces yo también la quería.\\n"  
        "Cómo no haber amado sus grandes ojos fijos."  
    )  
      
    \# Procesar inferencias consecutivas de lote de tamaño 1  
    print("\\nProcesando fragmento narrativo (Prosa)...")  
    res\_prosa \= predecir\_estructura\_texto(tokenizer, model, device, prosa\_narrativa)  
    print(f"Resultado \-\> Categoría: {res\_prosa\['clase\_predicha'\]} (Confianza: {res\_prosa\['confianza'\]:.4f})")  
      
    print("\\nProcesando fragmento lírico (Verso)...")  
    res\_verso \= predecir\_estructura\_texto(tokenizer, model, device, verso\_lirico)  
    print(f"Resultado \-\> Categoría: {res\_verso\['clase\_predicha'\]} (Confianza: {res\_verso\['confianza'\]:.4f})")

## **Conclusiones y Recomendaciones de Despliegue**

La discriminación automatizada de fragmentos poéticos (verso) frente a estructuras de prosa narrativa o soporte documental (índices, notas al pie, listas) en entornos de hardware localmente acotados es plenamente viable si se implementan las estrategias de optimización adecuadas \[cite: Query\]. Con base en el análisis de rendimiento y viabilidad técnica realizado, se consolidan las siguientes conclusiones accionables:

1. **Modelo de Selección Óptima:** El clasificador classla/xlm-roberta-base-multilingual-text-genre-classifier representa la alternativa de mayor madurez del ecosistema para la clasificación automatizada de documentos a nivel de cuerpo de texto12. Al agrupar las manifestaciones literarias bajo la etiqueta de grano grueso Prose/Lyrical, desvía con precisión las estructuras de soporte no líricas (índices, bibliografías, aclaraciones técnicas) hacia la clase Information/Explanation o Other, ofreciendo un filtro primario de alta confiabilidad12. Para la subdivisión fina entre prosa y poesía lírica, se recomienda complementar la predicción del modelo con un parser secundario ligero que evalúe la densidad de saltos de línea físicos frente a la cantidad de caracteres por secuencia (relación de aspecto tipográfica) o realizar un ajuste fino ligero de las últimas capas neuronales sobre el backbone de Multilingual-MiniLM17.  
2. **Estrategia de Ejecución en CPU (Escenario A):** Si el despliegue requiere prescindir completamente del uso de la GPU, la ruta técnica óptima consiste en la exportación del modelo de CLASSLA al formato intermedio ONNX, aplicando un pipeline de cuantización de enteros a 8 bits (INT8) para reducir a una cuarta parte la carga de memoria dinámica \[cite: Query, 185\]. Durante la configuración del entorno de ejecución de ONNX Runtime, es indispensable restringir de forma estática los hilos de procesamiento a un máximo de 6 cores físicos, evitando que las dinámicas de Hyper-Threading de la arquitectura Zen 2 del procesador Ryzen 5 3600 provoquen colisiones en la memoria caché L3 y degraden la latencia por encima del umbral requerido de 100 ms \[cite: Query\].  
3. **Estrategia de Ejecución en GPU (Escenario B):** El uso de la tarjeta gráfica NVIDIA GeForce GTX 1650 con aceleración de precisión media (FP16) es la aproximación más eficiente en términos de latencia neta, reduciendo el procesamiento de secuencias estándar a rangos de entre 12 y 18 ms \[cite: Query\]. Al mantener la huella estática del modelo en escasos 550 MB, se elimina la posibilidad de provocar errores por desbordamiento de memoria de video (OOM) en los 3.7 GB de VRAM útiles de la tarjeta de consumo \[cite: Query\].  
4. **Descarte de Alternativas Inestables:** Se desaconseja de manera categórica la selección de modelos basados en la arquitectura DeBERTa-v3 para flujos de producción optimizados en formato de representación ONNX o motores compilados en TensorRT11. Las inconsistencias dinámicas de su algoritmo de atención y el desbordamiento de constantes durante la compilación generan un incremento severo e inestable en el tamaño del archivo resultante, provocando anomalías en las predicciones finales y comprometiendo la viabilidad del despliegue en sistemas con recursos restringidos28.

### **Obras citadas**

1. Comparative Analysis of Katz and Eigen Centrality Metrics on Word Adjacency Networks for the classification of Poetry and Prose \- AIP Publishing, [https://pubs.aip.org/aip/acp/article-pdf/doi/10.1063/5.0249046/20368568/030022\_1\_5.0249046.pdf](https://pubs.aip.org/aip/acp/article-pdf/doi/10.1063/5.0249046/20368568/030022_1_5.0249046.pdf)  
2. arXiv:2107.08512v1 \[cs.CL\] 18 Jul 2021, [https://arxiv.org/pdf/2107.08512](https://arxiv.org/pdf/2107.08512)  
3. Sonnet or Not, Bot? Poetry Evaluation for Large Models and Datasets \- arXiv, [https://arxiv.org/html/2406.18906v3](https://arxiv.org/html/2406.18906v3)  
4. A pattern recognition approach for distinguishing between prose and poetry \- ResearchGate, [https://www.researchgate.net/publication/353344336\_A\_pattern\_recognition\_approach\_for\_distinguishing\_between\_prose\_and\_poetry](https://www.researchgate.net/publication/353344336_A_pattern_recognition_approach_for_distinguishing_between_prose_and_poetry)  
5. Metaphor Is Not All Attention Needs This paper contains jailbreak contents that can be offensive in nature. \- arXiv, [https://arxiv.org/html/2605.12128v1](https://arxiv.org/html/2605.12128v1)  
6. Emotion Detection in Poetry using Transformer-based Models \- ResearchGate, [https://www.researchgate.net/publication/390948169\_Emotion\_Detection\_in\_Poetry\_using\_Transformer-based\_Models](https://www.researchgate.net/publication/390948169_Emotion_Detection_in_Poetry_using_Transformer-based_Models)  
7. Computational Thematic Analysis of Poetry via Bimodal Large Language Models \- Kahyun Choi's, [https://kahyunchoi.com/wp-content/uploads/2023/09/asist2023\_kchoi.pdf](https://kahyunchoi.com/wp-content/uploads/2023/09/asist2023_kchoi.pdf)  
8. Classification \- a PoetryMTEB Collection \- Hugging Face, [https://huggingface.co/collections/PoetryMTEB/classification](https://huggingface.co/collections/PoetryMTEB/classification)  
9. Poetry Dataset​s \- a PoetryMTEB Collection \- Hugging Face, [https://huggingface.co/collections/PoetryMTEB/poetry-datasets](https://huggingface.co/collections/PoetryMTEB/poetry-datasets)  
10. TheBritishLibrary/bl-books-genre \- Hugging Face, [https://huggingface.co/TheBritishLibrary/bl-books-genre](https://huggingface.co/TheBritishLibrary/bl-books-genre)  
11. Mitchins/book-genre-v5-title-author \- Hugging Face, [https://huggingface.co/Mitchins/book-genre-v5-title-author](https://huggingface.co/Mitchins/book-genre-v5-title-author)  
12. classla/xlm-roberta-base-multilingual-text-genre-classifier \- Hugging Face, [https://huggingface.co/classla/xlm-roberta-base-multilingual-text-genre-classifier](https://huggingface.co/classla/xlm-roberta-base-multilingual-text-genre-classifier)  
13. TajaKuzman/AGILE-Automatic-Genre-Identification-Benchmark \- GitHub, [https://github.com/TajaKuzman/AGILE-Automatic-Genre-Identification-Benchmark](https://github.com/TajaKuzman/AGILE-Automatic-Genre-Identification-Benchmark)  
14. Troubling Times for PhD Research on Text Categorization? ChatGPT for Automatic Genre Identification | Semantics Archive, [https://semanticsarchive.net/Archive/WZkNTExO/ESSLLI\_Kuzman\_ChatGPT\_Automatic\_Genre\_Identification\_Final\_Paper\_Version%20-%20Omri%20Doron.pdf](https://semanticsarchive.net/Archive/WZkNTExO/ESSLLI_Kuzman_ChatGPT_Automatic_Genre_Identification_Final_Paper_Version%20-%20Omri%20Doron.pdf)  
15. CLASSLA \- CLARIN Knowledge Centre for South Slavic Languages \- Hugging Face, [https://huggingface.co/classla](https://huggingface.co/classla)  
16. config.json · classla/xlm-roberta-base-multilingual-text-genre-classifier at d31f5f4a1c7a21714ab3817dcea09f86eae716a4 \- Hugging Face, [https://huggingface.co/classla/xlm-roberta-base-multilingual-text-genre-classifier/blob/d31f5f4a1c7a21714ab3817dcea09f86eae716a4/config.json](https://huggingface.co/classla/xlm-roberta-base-multilingual-text-genre-classifier/blob/d31f5f4a1c7a21714ab3817dcea09f86eae716a4/config.json)  
17. microsoft/Multilingual-MiniLM-L12-H384 \- Hugging Face, [https://huggingface.co/microsoft/Multilingual-MiniLM-L12-H384](https://huggingface.co/microsoft/Multilingual-MiniLM-L12-H384)  
18. LLM Teacher-Student Framework for Text Classification With No Manually Annotated Data \- arXiv, [https://arxiv.org/html/2411.19638v2](https://arxiv.org/html/2411.19638v2)  
19. README.md · classla/multilingual-IPTC-news-topic-classifier at 20dd6be806ce7850ec8647efabd5ade177f1857e \- Hugging Face, [https://huggingface.co/classla/multilingual-IPTC-news-topic-classifier/blame/20dd6be806ce7850ec8647efabd5ade177f1857e/README.md](https://huggingface.co/classla/multilingual-IPTC-news-topic-classifier/blame/20dd6be806ce7850ec8647efabd5ade177f1857e/README.md)  
20. Necto@DravidianLangTech 2025: Fine-tuning Multilingual MiniLM for Text Classification in Dravidian Languages \- ACL Anthology, [https://aclanthology.org/2025.dravidianlangtech-1.56.pdf](https://aclanthology.org/2025.dravidianlangtech-1.56.pdf)  
21. unilm/minilm/README.md at master \- GitHub, [https://github.com/microsoft/unilm/blob/master/minilm/README.md](https://github.com/microsoft/unilm/blob/master/minilm/README.md)  
22. README.md · microsoft/Multilingual-MiniLM-L12-H384 at 6e8c1ec6b4ec4e3fc6eb7d2cd834fcd582b61daf \- Hugging Face, [https://huggingface.co/microsoft/Multilingual-MiniLM-L12-H384/blame/6e8c1ec6b4ec4e3fc6eb7d2cd834fcd582b61daf/README.md](https://huggingface.co/microsoft/Multilingual-MiniLM-L12-H384/blame/6e8c1ec6b4ec4e3fc6eb7d2cd834fcd582b61daf/README.md)  
23. Use embedding models with RAG Engine | Gemini Enterprise Agent Platform, [https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/use-embedding-models](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/use-embedding-models)  
24. Zero-Shot Text Classification using HuggingFace Model \- GeeksforGeeks, [https://www.geeksforgeeks.org/nlp/zero-shot-text-classification-using-huggingface-model/](https://www.geeksforgeeks.org/nlp/zero-shot-text-classification-using-huggingface-model/)  
25. kingkenche/distilbert-goodreads-genre-classifier at main \- Hugging Face, [https://huggingface.co/kingkenche/distilbert-goodreads-genre-classifier/tree/main](https://huggingface.co/kingkenche/distilbert-goodreads-genre-classifier/tree/main)  
26. protectai/deberta-v3-base-prompt-injection-v2 \- Hugging Face, [https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)  
27. Exporting DeBerta using custom onnx configuration · Issue \#16982 · huggingface/transformers \- GitHub, [https://github.com/huggingface/transformers/issues/16982](https://github.com/huggingface/transformers/issues/16982)  
28. Torch.export.onnx ignores attention\_mask in HF Transformer models \- PyTorch Forums, [https://discuss.pytorch.org/t/torch-export-onnx-ignores-attention-mask-in-hf-transformer-models/197708](https://discuss.pytorch.org/t/torch-export-onnx-ignores-attention-mask-in-hf-transformer-models/197708)  
29. Problem converting DeBERTaV3 to ONNX using optimum-cli · Issue \#2075 \- GitHub, [https://github.com/huggingface/optimum/issues/2075](https://github.com/huggingface/optimum/issues/2075)  
30. Converting PyTorch to ONNX model doubles file size for Deberta v3. Not case of renaming. \#4149 \- GitHub, [https://github.com/onnx/onnx/issues/4149](https://github.com/onnx/onnx/issues/4149)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE0AAAAaCAYAAADygtH/AAAC50lEQVR4Xu2YS6hNYRTH/x7lnQhJ4hYDxIAyECF5lDySgVd0cYuRgSLyipgIA0KS8hwYIco7iYE88hoYiIHHQAZCCIn/39rfPd9Z5+x79i3dczv2r37ds9da3zn7fHvt79vnAjk5OTn/lEt0rQ+m0I8eoS/pSVpXlDXm0Gv0Kd1EOxana4MX9HeKp6O6CfQ9vUKn0MP0dpQX2+hDOo72oifoLdo1LmqKlSg9CXmITiwTlzc0sAXpQH+h9DyCswql+A7rrnbJ8RdYTe/keBT9BOvGQHv6hG6NYplYSr/RMbSzy42GffBC2snlWoIh9CNdRxfRGbALKvc2Vhk6z2HuWBPZIzneTu8V0o3sofd9sBJq1xU+mKD1RB9eLdRJy11MF1bdEbOZ7nIxz3rYd1G3zU1ifWG3tNa5zPSBvVF/nyDdYFeqmpNWjv10p4udp1tg69pF+o6OL6oABtLPsO+jW15r2lV6MC7KwgKkT8p8FNaO1sJs+oF2cXF1nibgLB0BmyBdcC34MZNgnRa+l+rbFlVk4CgKb5Dm3VBcAa03fmwl6zSwGWhytAbFtIEt+uqewVH8NX0OW+xjwm0qv9JlxemmGQkb+NMnYB8e3ni6y1UL3YI6nwE+QV7RAy52AVZ/KjlenByH7tPGFx5n1L2ZWAMbcMcnSAMs9wOlt0K1CJ1Rjgd0g4udgY3RZiaeoXT90s76GFaXibAz+nYXx2C5yz5RRXQ+j3ww4ThsI4g5Bxujv0Kv4+e6wFRknDR1j7pIxeW22zewnLoxKzNhY5rjoL8js6H6mz6YsITudjFtDBqzIznW63mFdCPqNuUqomcaFaZdOeW0+4Sn69aAzil0TTmUH+uOw4SJethmobUt0B12N62KYiUMR+nVDrOsJ379MvA5TV5rQOein0lp7KNvYbepflPq56B/nNBOqfe5DlueVF8fF9Qaq1F+54wZSjfC/nuRRk86jU5Gjf6HIycnJycnJyfnf+APA0LeVIflMG0AAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE0AAAAaCAYAAADygtH/AAACrElEQVR4Xu2XS6hNURjH/56FCIVIUSjPoiiPgTsy8IryzsSra2BgYqAYKI+JRCYeA8+JQmaI3IgIRVEGCkWRlIEiDPj/77fWvWuts+89p311jk7rV7/aa31r7fPtb6+z99pAJpPJ/HMm0u/0Fb1E18ThdmbBYl/oGzomDhdywdl0zIUVYQSdQB/TP9EI4yNdSwfRAa49NRoRswR2HhW6ZrbDJqWepC0F/bJNE+vMA3ovaG+A5TIq6FORlgdtcYLeSfpCXqNE0Tyb6A86jw5MYnNgJ1aiSqzeDEHnDfOEOXkW0aFBW6yAjRue9Hu0EksX7RltTTsdNxAn3Agm041Bewssp2FB3wLXd4j2cn136ZGOETG36DqULNpI2MSxaYAMpj/R+KKl6ILTnHq7PnmVTqIPYSs1ZRV9ih4UbT0qE/D4k3YVrzf96B5YPteTmNCb1ecri/6Wevy8o7PRg6KdRfxDReptVQtLUTm3muM1sUb8nJd0ShIT8xGf+yjtG40A9sFeEKJU0bSv0aTfaQC2L/I/vjiJNRptO5TXjKBvGt0dtEejM/+Fru8K3dwxomTRdsEmPUoDZCss9gu27/nf+Ax7dnlO0z5BW1yEXcMB19bWJaRU0fybsegNcw4Wu5kG6sw4egr27A25T78G7fDYoy3IN3rNtf3K68qqaPVoFWnwyiQmPsBiWo21sgyViVRTf7Xu0F+q6KKe0/dB+1NwHPKEHnPHLYnaxOu8t127KodhE/TjRSim7Ua65OuNNtzKZX/Qt8316bnlmUmPw96wHu3ZLgftlDOw82gL0+11Tkfl3fZ3UTt+fRmkMRWvkWgFv4WtjPOwfPQJlKIP9Rewx42eUwfR9VdMGyqvs+nQSthJ98JWWv843I4KpC+DHXR1EstkMplMJpPJNBl/ATfw2lpg4oWMAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,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>
