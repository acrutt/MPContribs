import 'select2';
import {Spinner} from 'spin.js/spin';

var fields = ['formula', 'project', 'identifier'];
var subresources = ['structures', 'tables'];
var spinner = new Spinner({scale: 0.5, color: 'white'});

function get_single_selection(field) {
    var select = $('#'+field+'s_list').select2("data");
    return $.map(select, function(sel) { return sel['value']; }).join(',');
}

function get_selection(field) {
    return $.map(fields, function(f) {
        return (f !== field) ? get_single_selection(f) : '';
    });
}

function get_query(selection) {
    var query = {}; // _limit: 7
    if (selection.length > 3) { query['_fields'] = 'id,project,identifier,formula'; }
    $.each(selection, function(idx, sel) {
        if (idx < 3 && sel !== '') { query[fields[idx] + '__in'] = sel; }
        else if (idx >= 3 && sel) { query['_fields'] += ',' + subresources[idx-3]; }
    });
    return query;
}

function getData(field) {
    return function (params) {
        var query = get_query(get_selection(field));
        if (params.term) {
            if (field == 'project') {
                query['description__icontains'] = params.term;
            } else {
                query[field + '__contains'] = params.term;
            }
        }
        if (field == 'project') {
            query['_fields'] = 'id,title,project';
        } else {
            query['_fields'] = 'id,' + field;
        }
        return query;
    }
}

function processResult(d, field) {
    var id = d.hasOwnProperty('id') ? d['id'] : d[field];
    var text = d.hasOwnProperty('title') ? d['title']: d[field];
    return {id: id, text: text, value: d[field]};
}

function processResults(field) {
    return function (data) {
        var texts = new Set();
        var results = $.map(data['data'], function(d) {
            if (!texts.has(d[field])) {
                texts.add(d[field]);
                return processResult(d, field);
            }
        });
        return {results: results};
    }
}

function get_ajax(field, pk) {
    var endpoint = (field == 'project') ? 'projects/' : 'contributions/';
    if (pk !== null) { endpoint += pk + '/'; }
    var api_url = window.api['host'] + endpoint;
    return {
        url: api_url, headers: window.api['headers'],
        delay: 400, minimumInputLength: 2, maximumSelectionLength: 3,
        multiple: true, width: 'style',
        data: getData(field), processResults: processResults(field)
    }
}

function click_card(event) {
    event.preventDefault(); // To prevent following the link (optional)
    var cid = $(this).attr('id');
    return render_card(cid);
}

function render_card(cid) {
    $("#card").empty();
    var target = document.getElementById('spinner');
    spinner.spin(target);
    var url = window.api['host'] + 'cards/' + cid + '/';
    return $.get({url: url, headers: window.api['headers']}).done(function(response) {
        $('#card').html(response['html']);
        spinner.stop();
    });
}

function check_subresources(d) {
    var subs = $.map(subresources, function(sub) {
        if (d.hasOwnProperty(sub)) { return d[sub].length; }
    });
    for (var s = 0; s < subs.length; s++) {
        if (!subs[s]) { return false; }
    }
    // no subresource requirements set or all requirements true -> let pass
    return true;
}

function show_results(selection) {
    var target = document.getElementById('spinner');
    spinner.spin(target);
    var query = get_query(selection)
    var api_url = window.api['host'] + 'contributions/';
    return $.get({
        url: api_url, data: query, headers: window.api['headers']
    }).done(function(response) {
        $('#count').html(response['total_count']).parent().removeClass('is-hidden');
        $('#results').empty();
        $.each(response['data'], function(i, d) {
            if (check_subresources(d)) {
                var cid_url = $('<a/>', {'id': d['id'], 'text': d['id'].slice(-7)});
                cid_url.on('click', click_card);
                var cid = $('<td/>', {html: cid_url});
                var formula = $('<td/>', {text: d['formula']});
                var project = $('<td/>', {text: d['project']});
                var mp = 'https://materialsproject.org/materials/'
                var mpid = d['identifier'];
                if (mpid.startsWith('m')) {
                    mpid = $('<a/>', {href: mp + d['identifier'], text: d['identifier'], target: '_blank'});
                }
                var identifier = $('<td/>', {html: mpid});
                var tr = $('<tr/>');
                tr.append([cid, formula, project, identifier]);
                $('#results').append(tr);
            }
        });
        spinner.stop();
    });
}

function search(event) {
    event.preventDefault(); // To prevent following the link (optional)
    var selection = $.map(fields, function(f) { return get_single_selection(f); });
    var filtered_selection = selection.filter(function (el) { return el !== ''; });
    if (filtered_selection.length === 0) { console.log('no selection made'); return; }
    $('input:checkbox').each(function(idx, chbx) {
        selection.push(chbx.checked);
    });
    show_results(selection);
}

$(document).ready(function () {
    $.each(fields, function(idx, field) {
        $('#'+field+'s_list').select2({
            placeholder: 'Select '+field+'(s) ...',
            ajax: get_ajax(field, null)
        });
    });
    $('select').on('change', search);
    $('input:checkbox').on('change', search);
    show_results(['', '', 'mp-2715']).done(function() {
        var cid = $('#results').find('tr:first td:first a')[0].id;
        render_card(cid);
    });
    $('.select2').css({width: '100%'});
    $('.select2-search').css({width: 'auto'});
    $('.select2-search__field').css({width: '100%'});
});
