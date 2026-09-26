<?php

require_once (IBSINC."xml.php");
require_once (IBSINC."generator/generator.php");

/**
 */
class XmlGenerator extends IBSGenerator
{
	/**
	 * @access public
	 */
	function __construct($root, $element)
	{
		$this->root = $root;
		$this->element = $element;
	}
	function doArray($array)
	{
		return "<{$this->element}>".convDicToXML($array)."</{$this->element}>";
	}

	function init()
	{
		return "<{$this->root}>";
	}

	function dispose()
	{
		return "</{$this->root}>";
	}

}
?>