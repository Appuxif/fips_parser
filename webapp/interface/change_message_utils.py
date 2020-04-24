from django.contrib.admin.utils import *
from django.contrib.admin.models import *


# Меняем текст логов в админке
def get_change_message(self):
    """
    If self.change_message is a JSON structure, interpret it as a change
    string, properly translated.
    """
    if self.change_message and self.change_message[0] == '[':
        try:
            change_message = json.loads(self.change_message)
        except json.JSONDecodeError:
            return self.change_message
        messages = []
        for sub_message in change_message:
            if 'added' in sub_message:
                if sub_message['added']:
                    sub_message['added']['name'] = gettext(sub_message['added']['name'])
                    if 'fields' not in sub_message['added']:
                        sub_message['added']['fields'] = ''
                    else:
                        sub_message['added']['fields'] = get_text_list(
                            [gettext(field_name) for field_name in sub_message['added']['fields']], gettext('and')
                        )
                    messages.append(gettext('Added {name} “{object}”.\n{fields}').format(**sub_message['added']))
                else:
                    messages.append(gettext('Added.'))

            elif 'changed' in sub_message:
                sub_message['changed']['fields'] = get_text_list(
                    [gettext(field_name) for field_name in sub_message['changed']['fields']], gettext('and')
                )
                if 'name' in sub_message['changed']:
                    sub_message['changed']['name'] = gettext(sub_message['changed']['name'])
                    messages.append(gettext('Changed {name} “{object}”.\n{fields}').format(
                        **sub_message['changed']
                    ))
                else:
                    messages.append(gettext('Changed {fields}.').format(**sub_message['changed']))

            elif 'deleted' in sub_message:
                sub_message['deleted']['name'] = gettext(sub_message['deleted']['name'])
                messages.append(gettext('Deleted {name} “{object}”.').format(**sub_message['deleted']))

        change_message = ' '.join(msg[0].upper() + msg[1:] for msg in messages)
        return change_message or gettext('No fields changed.')
    else:
        return self.change_message


# Это объект из БД, куда складируются все логи админки
LogEntry.get_change_message = get_change_message


def construct_change_message(form, formsets, add):
    """
    Construct a JSON structure describing changes from a changed object.
    Translations are deactivated so that strings are stored untranslated.
    Translation happens later on LogEntry access.
    """
    # Evaluating `form.changed_data` prior to disabling translations is required
    # to avoid fields affected by localization from being included incorrectly,
    # e.g. where date formats differ such as MM/DD/YYYY vs DD/MM/YYYY.
    changed_data = form.changed_data
    with translation_override(None):
        # Deactivate translations while fetching verbose_name for form
        # field labels and using `field_name`, if verbose_name is not provided.
        # Translations will happen later on LogEntry access.
        changed_field_labels = _get_changed_field_labels_from_form(form, changed_data)

    change_message = []
    if add:
        change_message.append({'added': {}})
    elif form.changed_data:
        change_message.append({'changed': {'fields': changed_field_labels}})
    if formsets:
        with translation_override(None):
            for formset in formsets:
                for added_object in formset.new_objects:
                    for i, form in enumerate(formset.forms):
                        if added_object == form.cleaned_data.get('id', None):
                            break
                    print(formset.forms[i].changed_data)
                    print(formset.forms[i].cleaned_data)
                    changed_fields = [key for key in formset.forms[i].cleaned_data]
                    change_message.append({
                        'added': {
                            'name': str(added_object._meta.verbose_name),
                            'object': str(added_object),
                            'fields': _get_changed_field_labels_from_form(formset.forms[i], changed_fields),
                        }
                    })
                for changed_object, changed_fields in formset.changed_objects:
                    for i, form in enumerate(formset.forms):
                        if changed_object == form.cleaned_data.get('id', None):
                            break
                    change_message.append({
                        'changed': {
                            'name': str(changed_object._meta.verbose_name),
                            'object': str(changed_object),
                            'fields': _get_changed_field_labels_from_form(formset.forms[i], changed_fields),
                        }
                    })
                for deleted_object in formset.deleted_objects:
                    change_message.append({
                        'deleted': {
                            'name': str(deleted_object._meta.verbose_name),
                            'object': str(deleted_object),
                        }
                    })
    return change_message


def _get_changed_field_labels_from_form(form, changed_data):
    changed_field_labels = []
    for field_name in changed_data:
        value = form.cleaned_data[field_name]
        try:
            verbose_field_name = form.fields[field_name].label or field_name
        except KeyError:
            verbose_field_name = field_name
        changed_field_labels.append('[' + str(verbose_field_name) + ': "' + str(value) + '"]')
    return changed_field_labels