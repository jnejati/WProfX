from urllib.parse import urldefrag
from bokeh.models import LinearAxis, Range1d, CustomJS, HoverTool, BoxSelectTool
from bokeh.plotting import figure, output_file, show, ColumnDataSource
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
import json


class DrawWaterfall():
    def __init__(self, jsonFile, outputFile, lookup_id, order_lookup):
        self.json_file = jsonFile
        with open(self.json_file) as data_file:
            self.data = json.load(data_file)
        # end_time = data[-1][1]['endTime'] + 500
        self.end_time = 5000
        self.y_range = len(self.data) + 10
        self.line_width = 4
        output_file(outputFile)
        self.yr = Range1d(start=self.y_range, end=0)
        self.xr = Range1d(start=0, end=1.05 * self.end_time)
        self.lookup_id = lookup_id
        self.order_lookup = order_lookup

        hover = HoverTool(
            tooltips="""
                                  <div style='padding: 3px; width: 500px; word-break: break-all; word-wrap: break-word; text-align: left;'>
                                      <div>
                                          <div>
                                              <span style="font-weight: bold; font-size: 9px;">@desc</span>
                                          </div>
                                      </div>
                                      <div>
                                          <div>
                                              <span style=" font-size: 8px;">@o_url</span>
                                          </div>
                                      </div>
                                      <div>
                                          <div>
                                              <span style="font-size: 9px;">@o_size</span>
                                          </div>

                                      </div>
                                      <div>
                                          <div>
                                              <span style="font-size: 11px;">@o_stime</span>
                                          </div>

                                      </div>
                                      <div>
                                          <div>
                                              <span style="font-size: 11px;">@o_etime</span>
                                          </div>

                                      </div>

                                      <div>
                                          <div>
                                              <span style="font-size: 11px;">@o_time</span>
                                          </div>

                                      </div>
                                  </div>
                                  """
        )
        self.p = figure(plot_width=1250, plot_height=2100, tools=[hover, 'save,pan,wheel_zoom,box_zoom,reset,resize'],
                        y_range=self.yr,
                        x_range=self.xr, x_axis_location="above")
        # p.ygrid.grid_line_color = None
        self.p.xaxis.axis_label = 'Time (ms)'
        self.p.xaxis.axis_label_text_align = 'left'
        self.p.xaxis.axis_label_text_color = "#c8c8c8"
        self.p.xaxis.axis_label_text_font_size = '10pt'
        self.p.xaxis.axis_line_color = '#c8c8c8'
        self.p.xaxis.major_tick_line_color = '#c8c8c8'
        self.p.xaxis.major_label_text_color = '#c8c8c8'
        self.p.xaxis.major_label_text_align = 'left'
        self.p.xaxis.major_label_text_font_size = '10pt'
        self.p.xaxis.minor_tick_line_color = '#c8c8c8'
        self.p.xaxis.minor_tick_out = 0
        self.p.xgrid.grid_line_alpha = 0.5
        self.p.ygrid.grid_line_color = None
        self.p.yaxis.visible = False
        self.javascript_type_list = ['application/x-javascript', 'application/javascript', 'application/ecmascript',
                                     'text/javascript', 'text/ecmascript', 'application/json', 'javascript/text']
        self.css_type_list = ['text/css', 'css/text']
        self.text_type_list = ['evalhtml', 'text/html', 'text/plain', 'text/xml']
        self.colormap = dict(ctext='#2757ae', dtext="#a8c5f7", cjs="#c9780e", djs='#e8ae61', ccss="#13bd0d",
                             dcss='#8ae887',
                             cother="#eb5bc0", dother='#eb5bc0', img='#c79efa')

    def draw_from_json(self):
        for _index, _event in enumerate(self.data):
            if not _event['id'] == 'Deps':
                for _obj in _event['objs']:
                    _nodeId = _obj[0]
                    _nodeData = _obj[1]
                    try:
                        _startTime = round(_nodeData['startTime'], 2)
                    except:
                        print(_nodeData, _nodeData)
                        continue
                    try:
                        _endTime = round(_nodeData['endTime'], 2)
                    except:
                        print(_nodeId, _nodeData)
                        continue
                    _duration = round(_endTime - _startTime, 2)
                    ##########################################################################################
                    # Network
                    ##########################################################################################
                    if _nodeId.startswith('Network'):
                        if 'transferSize' in _nodeData:
                            _transferSize = _nodeData['transferSize']
                        else:
                            _transferSize = 0
                        _url = _nodeData['url']
                        _mimeType = _nodeData['mimeType']
                        y_index = (_index + 1)
                        if _mimeType in self.text_type_list:
                            color = self.colormap['dtext']
                        elif _mimeType in self.css_type_list:
                            color = self.colormap['dcss']
                        elif _mimeType in self.javascript_type_list:
                            color = self.colormap['djs']
                        elif _mimeType.startswith('image'):
                            color = self.colormap['img']
                        else:
                            color = self.colormap['dother']
                        _mimeType = _nodeId + ': ' + _nodeData['mimeType']
                        source = ColumnDataSource(
                            data=dict(
                                x=[_startTime, _endTime],
                                y=[y_index, y_index],
                                desc=[_mimeType, _mimeType],
                                o_url=[_url, _url],
                                o_size=[_transferSize, _transferSize],
                                o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                                o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                                o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                            ))
                        r = self.p.line('x', 'y', source=source,
                                   line_color=color,
                                   line_width=self.line_width, line_cap='round', name='myline')
                    ##########################################################################################
                    # Loading
                    ##########################################################################################
                    elif _nodeId.startswith('Loading'):
                        _desc = _nodeData['name'] + ': ' + _nodeId
                        _url = ' '
                        _styleSheetUrl = ' '
                        if _nodeData['name'] == 'ParseHTML' and 'url' in _nodeData:
                            if _nodeData['url'] is not None:

                                _url = _nodeData['url']
                                y_index = _index + 1
                                color = self.colormap['ctext']
                            else:
                                continue
                        elif _nodeData['name'] == 'ParseAuthorStyleSheet' and 'styleSheetUrl' in _nodeData:
                            if _nodeData['styleSheetUrl'] is not None:
                                _styleSheetUrl = _nodeData['styleSheetUrl']
                                y_index = _index + 1
                                color = self.colormap['ccss']
                            else:
                                continue
                        source = ColumnDataSource(
                            data=dict(
                                x=[_startTime, _endTime],
                                y=[y_index, y_index],
                                desc=[_desc, _desc],
                                o_url=[_url, _url],
                                o_size=[_styleSheetUrl, _styleSheetUrl],
                                o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                                o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                                o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                            ))
                        r = self.p.line('x', 'y', source=source,
                                   line_color=color,
                                   line_width=self.line_width, line_cap='round', name='myline')
                    ##########################################################################################
                    # Scripting
                    ##########################################################################################
                    elif _nodeId.startswith('Scripting'):
                        _url = _nodeData['url']
                        _desc = _nodeId
                        color = self.colormap['cjs']
                        y_index = _index + 1
                        source = ColumnDataSource(
                            data=dict(
                                x=[_startTime, _endTime],
                                y=[y_index, y_index],
                                desc=[_desc, _desc],
                                o_url=[_url, _url],
                                o_size=['Scripting', 'Scripting'],
                                o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                                o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                                o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                            ))
                        r = self.p.line('x', 'y', source=source,
                                   line_color=color,
                                   line_width=self.line_width, line_cap='round', name='myline')
                    ##########################################################################################
                    # Rendering
                    ##########################################################################################
                    elif _nodeId.startswith('Rendering'):
                        _desc = _nodeData['name']
                        color = '#9b82e3'
                        if _desc == 'UpdateLayerTree':
                            y_index = (len(self.data) + 1)
                        elif _desc == 'Layout':
                            y_index = (len(self.data) + 2)
                        elif _desc == 'HitTest':
                            y_index = (len(self.data) + 3)
                        elif _desc == 'RecalculateStyles':
                            y_index = (len(self.data) + 4)
                        source = ColumnDataSource(
                            data=dict(
                                x=[_startTime, _endTime],
                                y=[y_index, y_index],
                                desc=[_desc + ': ', _desc + ': '],
                                o_url=['', ''],
                                o_size=['Rendering', 'Rendering'],
                                o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                                o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                                o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                            ))
                        r = self.p.line('x', 'y', source=source,
                                   line_color=color,
                                   line_width=self.line_width, line_cap='round', name='myline')
                    ##########################################################################################
                    # Painting is one thread
                    ##########################################################################################
                    elif _nodeId.startswith('Paint'):
                        _desc = _nodeData['name']
                        color = '#76b169'
                        y_index = (len(self.data) + 5)
                        source = ColumnDataSource(
                            data=dict(
                                x=[_startTime, _endTime],
                                y=[y_index, y_index],
                                desc=[_desc + ': ', _desc + ': '],
                                o_url=['', ''],
                                o_size=['Painting', 'Painting'],
                                o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                                o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                                o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                            ))
                        r = self.p.line('x', 'y', source=source,
                                        line_color=color,
                                        line_width=self.line_width, name='myline')

    def draw_critical_path(self, cp):
        i = 0
        for _dep in self.data[-1]['objs']:
            a1_id = _dep['a1']
            a2_id = _dep['a2']
            if (a1_id in cp) and (a2_id == cp[cp.index(a1_id) + 1]):
                #print(a1_id, a2_id, i)
                a1_start = self.lookup_id[a1_id]['startTime']
                a2_start = self.lookup_id[a2_id]['startTime']
                a1_end = self.lookup_id[a1_id]['endTime']
                a2_end = self.lookup_id[a2_id]['endTime']
                a1_y = self.order_lookup[a1_id] + 1
                a2_y = self.order_lookup[a2_id] + 1
                if a1_y == a2_y:
                    if not _dep['time'] == -1:
                        a1_end = _dep['time']
                    self.p.line([a1_end, a2_start], [a1_y, a1_y], line_color='red',
                                line_width=2, line_cap='square')
                else:
                    if not _dep['time'] == -1:
                        a1_end = _dep['time']
                    self.p.line([a1_end, a1_end], [a1_y, a2_y], line_color='red',
                                line_width=2, line_cap='square')
                    if a1_end < a2_start: #???
                        self.p.circle([a1_end], [a2_y], line_color='red', size=1)
                    self.p.line([a1_end, a2_start], [a2_y, a2_y], line_color='red',
                                line_width=2, line_cap='square')


    def showPlot(self):
        show(self.p)

    def draw_from_dict(self, y_order_url_lookup, data):
        for obj in data:
            _nodeId = obj[0]
            _nodeData = obj[1]
            try:
                _startTime = round(_nodeData['startTime'], 2)
            except:
                print(_nodeData, _nodeData)
                continue
            try:
                _endTime = round(_nodeData['endTime'], 2)
            except:
                print(_nodeId, _nodeData)
                continue
            _duration = round(_endTime - _startTime, 2)
            ##########################################################################################
            # Network
            ##########################################################################################
            if _nodeId.startswith('Network'):
                if 'transferSize' in _nodeData:
                    _transferSize = _nodeData['transferSize']
                else:
                    _transferSize = 0
                _url = _nodeData['url']
                _mimeType = _nodeData['mimeType']
                y_index = (y_order_url_lookup[urldefrag(_url)[0]] + 1)
                if _mimeType in self.text_type_list:
                    color = self.colormap['dtext']
                elif _mimeType in self.css_type_list:
                    color = self.colormap['dcss']
                elif _mimeType in self.javascript_type_list:
                    color = self.colormap['djs']
                elif _mimeType.startswith('image'):
                    color = self.colormap['img']
                else:
                    color = self.colormap['dother']
                _mimeType = _nodeId + ': ' + _nodeData['mimeType']
                source = ColumnDataSource(
                    data=dict(
                        x=[_startTime, _endTime],
                        y=[y_index, y_index],
                        desc=[_mimeType, _mimeType],
                        o_url=[_url, _url],
                        o_size=[_transferSize, _transferSize],
                        o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                        o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                        o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                    ))
                r = self.p.line('x', 'y', source=source,
                           line_color=color,
                           line_width=self.line_width, line_cap='round', name='myline')
            ##########################################################################################
            # Loading
            ##########################################################################################
            elif _nodeId.startswith('Loading'):
                _desc = _nodeData['name']
                _url = ' '
                _styleSheetUrl = ' '
                if _desc == 'ParseHTML' and 'url' in _nodeData:
                    if _nodeData['url'] is not None:
                        _url = _nodeData['url']
                        y_index = (y_order_url_lookup[urldefrag(_url)[0]] + 1)
                        color = self.colormap['ctext']
                    else:
                        continue
                elif _desc == 'ParseAuthorStyleSheet' and 'styleSheetUrl' in _nodeData:
                    if _nodeData['styleSheetUrl'] is not None:
                        _styleSheetUrl = _nodeData['styleSheetUrl']
                        y_index = (y_order_url_lookup[urldefrag(_styleSheetUrl)[0]] + 1)
                        color = self.colormap['ccss']
                    else:
                        continue
                source = ColumnDataSource(
                    data=dict(
                        x=[_startTime, _endTime],
                        y=[y_index, y_index],
                        desc=[_desc, _desc],
                        o_url=[_url, _url],
                        o_size=[_styleSheetUrl, _styleSheetUrl],
                        o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                        o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                        o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                    ))
                r = self.p.line('x', 'y', source=source,
                           line_color=color,
                           line_width=self.line_width, line_cap='round', name='myline')
            ##########################################################################################
            # Scripting
            ##########################################################################################
            elif _nodeId.startswith('Scripting'):
                _url = _nodeData['url']
                _desc = ' '
                color = self.colormap['cjs']
                y_index = (y_order_url_lookup[urldefrag(_url)[0]] + 1)
                source = ColumnDataSource(
                    data=dict(
                        x=[_startTime, _endTime],
                        y=[y_index, y_index],
                        desc=[_desc, _desc],
                        o_url=[_url, _url],
                        o_size=['Scripting', 'Scripting'],
                        o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                        o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                        o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                    ))
                r = self.p.line('x', 'y', source=source,
                           line_color=color,
                           line_width=self.line_width, line_cap='round', name='myline')
            ##########################################################################################
            # Rendering
            ##########################################################################################
            elif _nodeId.startswith('Rendering'):
                _desc = _nodeData['name']
                color = '#9b82e3'
                if _desc == 'UpdateLayerTree':
                    y_index = (len(y_order_url_lookup) + 1)
                elif _desc == 'Layout':
                    y_index = (len(y_order_url_lookup) + 2)
                elif _desc == 'HitTest':
                    y_index = (len(y_order_url_lookup) + 3)
                elif _desc == 'RecalculateStyles':
                    y_index = (len(y_order_url_lookup) + 4)
                source = ColumnDataSource(
                    data=dict(
                        x=[_startTime, _endTime],
                        y=[y_index, y_index],
                        desc=[_desc + ': ', _desc + ': '],
                        o_url=['', ''],
                        o_size=['Rendering', 'Rendering'],
                        o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                        o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                        o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                    ))
                r = self.p.line('x', 'y', source=source,
                           line_color=color,
                           line_width=self.line_width, line_cap='round', name='myline')

            ##########################################################################################
            # Painting
            ##########################################################################################
            elif _nodeId.startswith('Paint'):
                _desc = _nodeData['name']
                color = '#76b169'
                y_index = (len(y_order_url_lookup) + 5)
                source = ColumnDataSource(
                    data=dict(
                        x=[_startTime, _endTime],
                        y=[y_index, y_index],
                        desc=[_desc + ': ', _desc + ': '],
                        o_url=['', ''],
                        o_size=['Painting', 'Painting'],
                        o_stime=['s: ' + str(_startTime) + ' ms', 's: ' + str(_startTime) + ' ms'],
                        o_etime=['e: ' + str(_endTime) + ' ms', 'e: ' + str(_endTime) + ' ms'],
                        o_time=['dur: ' + str(_duration) + ' ms', 'dur: ' + str(_duration) + ' ms']
                    ))
                r = self.p.line('x', 'y', source=source,
                           line_color=color,
                           line_width=self.line_width, name='myline')

    def draw_dependents(self, dep):
        a1_id = dep['a1']
        a2_id = dep['a2']
        a1_start = self.lookup_id[a1_id]['startTime']
        a2_start = self.lookup_id[a2_id]['startTime']
        a1_end = self.lookup_id[a1_id]['endTime']
        a2_end = self.lookup_id[a2_id]['endTime']
        a1_y = self.order_lookup[a1_id] + 1
        a2_y = self.order_lookup[a2_id] + 1
        if a1_y == a2_y:
            if not dep['time'] == -1:
                a1_end = dep['time']
            self.p.line([a1_end, a2_start ], [a1_y, a1_y], line_color='black',
                        line_width=1, line_cap='square')
        else:
            if not dep['time'] == -1:
                a1_end = dep['time']
            self.p.line([a1_end, a1_end ], [a1_y, a2_y], line_color='black',
                        line_width=0.5, line_cap='square')
            if a1_end < a2_start:
                self.p.circle([a1_end], [a2_y], line_color='black', size = 2)
            self.p.line([a1_end, a2_start], [a2_y, a2_y], line_color='black',
                        line_width=0.5, line_cap='square')

    def draw_all_dependency(self):
        for dep in self.data[-1]['objs']:
            self.draw_dependents(dep)



#_plot = DrawWaterfall('./results/zdnet.json', 'line.html')
#_plot.draw_from_json()
#_plot.draw_dependency()
#_plot.showPlot()
# draw dep
