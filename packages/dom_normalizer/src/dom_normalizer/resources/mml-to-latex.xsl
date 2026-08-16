<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:m="http://www.w3.org/1998/Math/MathML"
    exclude-result-prefixes="m">

    <xsl:output method="text" encoding="UTF-8"/>

    <!-- Root element -->
    <xsl:template match="m:math">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Identifiers (variables) -->
    <xsl:template match="m:mi">
        <xsl:value-of select="."/>
    </xsl:template>

    <!-- Numbers -->
    <xsl:template match="m:mn">
        <xsl:value-of select="."/>
    </xsl:template>

    <!-- Operators -->
    <xsl:template match="m:mo">
        <xsl:text> </xsl:text>
        <xsl:value-of select="."/>
        <xsl:text> </xsl:text>
    </xsl:template>

    <!-- Rows (grouping) -->
    <xsl:template match="m:mrow">
        <xsl:apply-templates/>
    </xsl:template>

    <!-- Superscript -->
    <xsl:template match="m:msup">
        <xsl:apply-templates select="*[1]"/>
        <xsl:text>^{</xsl:text>
        <xsl:apply-templates select="*[2]"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- Subscript -->
    <xsl:template match="m:msub">
        <xsl:apply-templates select="*[1]"/>
        <xsl:text>_{</xsl:text>
        <xsl:apply-templates select="*[2]"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- Fraction -->
    <xsl:template match="m:mfrac">
        <xsl:text>\frac{</xsl:text>
        <xsl:apply-templates select="*[1]"/>
        <xsl:text>}{</xsl:text>
        <xsl:apply-templates select="*[2]"/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- Square root -->
    <xsl:template match="m:msqrt">
        <xsl:text>\sqrt{</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>}</xsl:text>
    </xsl:template>

    <!-- Text -->
    <xsl:template match="m:mtext">
        <xsl:value-of select="."/>
    </xsl:template>

    <!-- Default for unknown elements: just process children -->
    <xsl:template match="*">
        <xsl:apply-templates/>
    </xsl:template>

</xsl:stylesheet>