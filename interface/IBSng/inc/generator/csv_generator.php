<?php

require_once (IBSINC."csv.php");
require_once (IBSINC."generator/header_generator.php");

/**
 * used to crate CSV output
 */
class OutputCSVGenerator extends IBSGenerator
{
	/**
	 * @access public
	 */
	function __construct($csv, $file_name)
	{
		HeaderGenerator :: assignHeader("TEXT", $file_name);
		$this->csv = new CSVGenerator($csv);
	}

	function doArray($array)
	{
		$this->csv->doArray($array);
	}
}
?>