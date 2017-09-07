def float_to_tex(f,
	max_len=4,
	):
	"""Reformat float to tex syntax

	Parameters
	----------

	f : float
		Float to format.
	max_len : int
		Maximum digit length of output strings.
	"""

	if f >= 10**-max_len and f <= 10**max_len:
		f_str_template = "{{:.{}g}}".format(max_len)
		f_str = f_str_template.format(f)
	else:
		f_str = "{:e}".format(f)
		f_decimals, f_exponent = f_str.split("e")
		f_str = "{} \\times 10^{{{}}}".format(f_decimals[:max_len],f_exponent)
	return f_str

def inline_anova(df, factor,
        style="python",
        ):
        """Typeset factor summary from statsmodels-style anova DataFrame for inline mention.

        Parameters
        ----------
        df : pandas.DataFrame
                Pandas DataFrame object containing an ANOVA summary.
        factor : str
                String indicating the factor of interest from the summary given by `df`.
        style : {"python", "tex"}
                What formatting to apply to the string. A simple Python compatible string is returned when selecting "python", whereas a fancier output (decorated with TeX syntax) is returned if selecting "tex".
        """

        if style == "python":
		inline = "F({:g},{:g})={:2G}, p={:3G}".format(
                        df["df"][factor],
                        df["df"]["Residual"],
                        df["F"][factor],
                        df["PR(>F)"][factor],
                        )
        elif style == "tex":
		degrees_of_freedom = float_to_tex(df["df"][factor])
		degrees_of_freedom_rest = float_to_tex(df["df"]["Residual"])
		f_string = float_to_tex(df["F"][factor])
		p_string = float_to_tex(df["PR(>F)"][factor])
                inline = "$F_{{{},{}}}={},\\, p={}$".format(
                        degrees_of_freedom,
                        degrees_of_freedom_rest,
                        f_string,
                        p_string,
                        )

        return inline

