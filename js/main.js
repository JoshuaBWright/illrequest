//define:
ill_dark_gold = '#c9a721';
ill_label_blue = '#929DCC';

function highlight(ele,bgcolor) {
	ele.style.backgroundColor = bgcolor;
	}

function colortext(ele,color) {
	ele.style.color = color;
	}

function hide(id) {
	element(id).style.display="none";
	}

function show(id) {
	element(id).style.display="block";
	}

function element(id) {
	return document.getElementById(id);
	}

function removeElement(id) {
	ele=document.getElementById(id);
	ele_parent = ele.parentNode;
	ele_parent.removeChild(ele);
	}

function decrement(ele_name) {
	if (ele_name != null) {
		eles = document.getElementsByName(ele_name);
		for (var inc=0; inc<eles.length; inc++) {
			num_ele = eles[inc];
			num_txt = num_ele.innerHTML;
			number = parseInt(num_txt);
			number -= 1;
			num_ele.innerHTML = number.toString();
			}//endfor
		}//endif
	}//endfunction

function parent_with_name_for_element(parent_name,ele) {
	while (ele.parentNode != null) {
		if (ele.parentNode.getAttribute('name') == parent_name) {
			return ele.parentNode;
			}//endif
		else {
			ele = ele.parentNode;
			}
		}//endwhile
	return ele;
	}//endfunction

function submit(page,type,args,handler) {
	connection = new XHConn();
	connection.connect(page,type,args,handler);
	}

function post_handler() {
	}

function display_request_edit_form(oXML) {
	if (oXML != null) {
		rxml = oXML.responseXML;
		elem = rxml.getElementsByName('ill_request_form_container')[0];
		keyfield = rxml.getElementsByName('subcontainer_id')[0];
		container = document.getElementById(keyfield.firstChild.nodeValue);
		container.innerHTML = oXML.responseText;
		attach_admin_request_validators('request_validation_errors','request_error_message_area');
		container.style.display="block";
		}
	else {
		alert('Attempt to retrieve the request data failed!');
		} //endifelse
	} //endfunction
	
function attach_admin_request_validators(container_id,text_area_id) {
	var validator = new FormValidator('ill_request_form', [{
		name: 'title',
		display: 'title',    
		rules: 'required'
	}, {
		name: 'fullCitation',
		display: 'full citation',    
		rules: 'required'
	}, {
		name: 'pubDay',
		display: 'publication day',
		rules: 'required|numeric|min_length[1]|max_length[2]|greater_than[0]|less_than[32]'
	}, {
		name: 'pubMonth',
		display: 'publication month',
		rules: 'required|numeric|min_length[1]|max_length[2]|greater_than[0]|less_than[13]'
	}, {
		name: 'pubYear',
		display: 'publication year',
		rules: 'required|numeric|exact_length[4]|greater_than[999]'
	}, {
		name: 'dueDay',
		display: 'due day',
		rules: 'required|numeric|min_length[1]|max_length[2]|greater_than[0]|less_than[32]'
	}, {
		name: 'dueMonth',
		display: 'due month',
		rules: 'required|numeric|min_length[1]|max_length[2]|greater_than[0]|less_than[13]'
	}, {
		name: 'dueYear',
		display: 'due year',
		rules: 'required|numeric|exact_length[4]|greater_than[999]'
	}, {
		name: 'modifiedWhy',
		display: 'reason for edit',
		rules: 'required'
	}, {
		name: 'volumeNumber',
		display: 'volume number',
		rules: 'numeric'
	}], function(errors, event) {
		if (errors.length > 0) {
    		var errorString = '<span class="red_emphasis">&iexcl;Atención por favor! » There are some problems with your request…</span><ul>';
    
	        for (var i = 0, errorLength = errors.length; i < errorLength; i++) {
	            errorString += '<li class="alertlist">' + errors[i].message + '</li>';
	        }
    		errorString += '</ul>';
    		
    		show(container_id);
    		error_field = document.getElementById(text_area_id);
    		error_field.innerHTML = errorString;
		}//endfunction
	});//endassignment
	}//endfunction

function attach_user_request_validators(container_id,text_area_id) {
	var validator = new FormValidator('ill_request_form', [{
		name: 'title',
		display: 'title',    
		rules: 'required'
	}, {
		name: 'fullCitation',
		display: 'full citation',    
		rules: 'required'
	}, {
		name: 'pubDay',
		display: 'publication day',
		rules: 'required|numeric|min_length[1]|max_length[2]|greater_than[0]|less_than[32]'
	}, {
		name: 'pubMonth',
		display: 'publication month',
		rules: 'required|numeric|min_length[1]|max_length[2]|greater_than[0]|less_than[13]'
	}, {
		name: 'pubYear',
		display: 'publication year',
		rules: 'required|numeric|exact_length[4]|greater_than[999]'
	}, {
		name: 'description',
		display: 'description (why requesting)',
		rules: 'required'
	}, {
		name: 'volumeNumber',
		display: 'volume number',
		rules: 'numeric'
	}, { 
		name: 'requesterFullName',
		display: 'your full name',
		rules: 'required'
	}], function(errors, event) {
		if (errors.length > 0) {
    		var errorString = '<span class="red_emphasis">&iexcl;Atención por favor! » There are some problems with your request…</span><ul>';
    
	        for (var i = 0, errorLength = errors.length; i < errorLength; i++) {
	            errorString += '<li class="alertlist">' + errors[i].message + '</li>';
	        }
    		errorString += '</ul>';
    		
    		show(container_id);
    		error_field = document.getElementById(text_area_id);
    		error_field.innerHTML = errorString;
		}
	});
	}

function add_query_parameter_field(form_id,index) {
	
	}