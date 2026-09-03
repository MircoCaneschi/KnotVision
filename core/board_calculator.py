import math
from PySide6.QtGui import QPolygon
from PySide6.QtCore import QPoint, Qt

class BoardCalculator:
    """
    Core class responsible for performing all mathematical and geometric calculations (tKnot, DEB, etc.)
    for the board and the knots.
    """
    def __init__(self):
        pass

    def calculate_knot_results(self, board, knots, current_knot):
        """
        Calculate results for the current knot.
        Returns:
            dict: Dictionary with parameters tKnot, mKnot, tKAR, etc.
        """
        if not board or not current_knot or not knots:
            return self._empty_results()

        # Convert knots to the standard coordinate system for formulas
        standard_knots = [self._to_standard_knot(k, board) for k in knots]
        current_knot_std = self._to_standard_knot(current_knot, board)

        # Build polygons for all knots
        polygons = {}
        for knot in standard_knots:
            polygons[knot.knot_no] = self._create_polygon(knot, board)

        # Filter knots in interval (-150 to +150 mm)
        interval_knots = [k for k in standard_knots if abs(k.x - current_knot_std.x) <= 150]
        
        # Calculate individual parameters
        res = {}
        res["tKnot"] = self._tKnot(current_knot_std, board, polygons)
        res["mKnot"] = self._mKnot(current_knot_std, board, polygons)
        res["tKAR"] = self._tKAR(current_knot_std, board, interval_knots, polygons)
        
        mkar_l = self._mKAR_Left(current_knot_std, board, interval_knots, polygons)
        res["mKAR_L"] = mkar_l
        mkar_r = self._mKAR_Right(current_knot_std, board, interval_knots, polygons)
        res["mKAR_R"] = mkar_r
        res["mKAR"] = max(mkar_l, mkar_r) if mkar_l is not None and mkar_r is not None else 0.0

        res["DEB"] = self._DEB(current_knot_std, board)
        res["DAB"] = self._DAB(current_knot_std, board, interval_knots)
        res["DEK"] = self._DEK(current_knot_std, board)
        res["EEB"] = abs(self._EEB(current_knot_std, board))
        res["EAB"] = self._EAB(board, interval_knots)

        # Formatting values to strings with 2 decimals
        for k, v in res.items():
            if v is not None:
                res[k] = f"{v:.2f}"
            else:
                res[k] = "N/A"

        res["SplayKnot"] = "1" if self._SplayKnot(current_knot_std, board) else "0"

        return res

    def _empty_results(self):
        keys = ["tKnot", "mKnot", "tKAR", "mKAR_L", "mKAR_R", "mKAR", "DEB", "DAB", "DEK", "EEB", "EAB"]
        empty_res = {k: "0.00" for k in keys}
        empty_res["SplayKnot"] = "0"
        return empty_res

    def _val(self, v):
        return v if v is not None else -1

    def _to_standard_knot(self, knot, board):
        """
        Converts a knot from the LocalKnot coordinate system to the 'standard' one 
        used by the mathematical formulas:
        - Side 3 and 4 remain unchanged.
        - Side 1 (top): z originates from the right side instead of left (z1 = height - z2).
        - Side 2 (right): z originates from the top side instead of bottom (z1 = base - z2).
        """
        class _StdKnot: pass
        std_k = _StdKnot()
        std_k.knot_no = knot.knot_no
        std_k.x = knot.x
        std_k.pith_z = getattr(knot, 'pith_z', None)
        std_k.pith_y = getattr(knot, 'pith_y', None)
        std_k.is_pruned_knot = getattr(knot, 'is_pruned_knot', False)
        std_k.pruned_z1 = getattr(knot, 'pruned_z1', None)
        std_k.pruned_y1 = getattr(knot, 'pruned_y1', None)
        std_k.pruned_z2 = getattr(knot, 'pruned_z2', None)
        std_k.pruned_y2 = getattr(knot, 'pruned_y2', None)
        
        std_k.side1_dmin = knot.side1_dmin
        std_k.side2_dmin = knot.side2_dmin
        std_k.side3_z1 = knot.side3_z1
        std_k.side3_z2 = knot.side3_z2
        std_k.side3_dmin = knot.side3_dmin
        std_k.side4_z1 = knot.side4_z1
        std_k.side4_z2 = knot.side4_z2
        std_k.side4_dmin = knot.side4_dmin
        
        # Side 1 conversion
        if knot.side1_z1 is not None and knot.side1_z2 is not None:
            std_k.side1_z1 = board.height - knot.side1_z2
            std_k.side1_z2 = board.height - knot.side1_z1
        else:
            std_k.side1_z1 = knot.side1_z1
            std_k.side1_z2 = knot.side1_z2
            
        # Side 2 conversion
        if knot.side2_z1 is not None and knot.side2_z2 is not None:
            std_k.side2_z1 = board.base - knot.side2_z2
            std_k.side2_z2 = board.base - knot.side2_z1
        else:
            std_k.side2_z1 = knot.side2_z1
            std_k.side2_z2 = knot.side2_z2
            
        return std_k

    def _create_polygon(self, knot, board):
        poly = QPolygon()
        
        # Mapping properties to match Java array naming (old java reference code)
        t_z1, t_z2 = self._val(knot.side1_z1), self._val(knot.side1_z2)
        r_y1, r_y2 = self._val(knot.side2_z1), self._val(knot.side2_z2)
        b_z1, b_z2 = self._val(knot.side3_z1), self._val(knot.side3_z2)
        l_y1, l_y2 = self._val(knot.side4_z1), self._val(knot.side4_z2)
        p_z, p_y = self._val(knot.pith_z), self._val(knot.pith_y)

        b_width = board.height  # board_width in Java corresponds to height (z dimension)
        b_thick = board.base    # board_thickness in Java corresponds to base (y dimension)

        if (t_z1 >= 0 and t_z2 >= 0) and (l_y2 >= 0 and l_y1 >= 0) and (p_y >= 0 and p_z >= 0):
            poly.append(QPoint(0, l_y2))
            poly.append(QPoint(0, l_y1))
            poly.append(QPoint(t_z1, 0))
            poly.append(QPoint(t_z2, 0))
            poly.append(QPoint(p_z, p_y))
        else:
            if p_y >= 0 and p_z >= 0:
                poly.append(QPoint(p_z, p_y))
            if t_z1 >= 0 and t_z2 >= 0:
                poly.append(QPoint(t_z1, 0))
                poly.append(QPoint(t_z2, 0))
            if r_y1 >= 0 and r_y2 >= 0:
                poly.append(QPoint(b_width, r_y1))
                poly.append(QPoint(b_width, r_y2))
            if b_z2 >= 0 and b_z1 >= 0:
                poly.append(QPoint(b_z2, b_thick))
                poly.append(QPoint(b_z1, b_thick))
            if l_y2 >= 0 and l_y1 >= 0:
                poly.append(QPoint(0, l_y2))
                poly.append(QPoint(0, l_y1))
                
        return poly

    def _tKnot(self, current_knot, board, polygons):
        knot_area = 0
        total_area = 0
        poly = polygons[current_knot.knot_no]
        b_width = board.height
        b_thick = board.base
        
        for x in range(b_width):
            for y in range(b_thick):
                total_area += 1
                if poly.containsPoint(QPoint(x, y), Qt.FillRule.OddEvenFill):
                    knot_area += 1
                    
        return knot_area / total_area if total_area > 0 else 0.0

    def _mKnot(self, current_knot, board, polygons):
        b_width = board.height
        b_thick = board.base
        poly = polygons[current_knot.knot_no]
        
        area_left_margin = 0
        knot_area_left_margin = 0
        area_right_margin = 0
        knot_area_right_margin = 0
        
        limit_left = round(b_width * 0.25)
        for x in range(limit_left):
            for y in range(b_thick):
                area_left_margin += 1
                if poly.containsPoint(QPoint(x, y), Qt.FillRule.OddEvenFill):
                    knot_area_left_margin += 1
                    
        limit_right = round(b_width * 0.75)
        for x in range(limit_right, b_width):
            for y in range(b_thick):
                area_right_margin += 1
                if poly.containsPoint(QPoint(x, y), Qt.FillRule.OddEvenFill):
                    knot_area_right_margin += 1
                    
        mKnot_left = knot_area_left_margin / area_left_margin if area_left_margin > 0 else 0.0
        mKnot_right = knot_area_right_margin / area_right_margin if area_right_margin > 0 else 0.0
        
        return min(max(mKnot_left, mKnot_right), 1.0)

    def _tKAR(self, current_knot, board, interval_knots, polygons):
        b_width = board.height
        b_thick = board.base
        
        knots_area = 0
        total_area = 0
        
        for x in range(b_width):
            for y in range(b_thick):
                total_area += 1
                pt = QPoint(x, y)
                for k in interval_knots:
                    if polygons[k.knot_no].containsPoint(pt, Qt.FillRule.OddEvenFill):
                        knots_area += 1
                        break
                        
        return knots_area / total_area if total_area > 0 else 0.0

    def _mKAR_Left(self, current_knot, board, interval_knots, polygons):
        b_width = board.height
        b_thick = board.base
        
        knots_area = 0
        total_area = 0
        
        limit = round(b_width * 0.25)
        for x in range(limit):
            for y in range(b_thick):
                total_area += 1
                pt = QPoint(x, y)
                for k in interval_knots:
                    if polygons[k.knot_no].containsPoint(pt, Qt.FillRule.OddEvenFill):
                        knots_area += 1
                        break
                        
        val = knots_area / total_area if total_area > 0 else 0.0
        return min(val, 1.0)

    def _mKAR_Right(self, current_knot, board, interval_knots, polygons):
        b_width = board.height
        b_thick = board.base
        
        knots_area = 0
        total_area = 0
        
        limit = round(b_width * 0.75)
        for x in range(limit, b_width):
            for y in range(b_thick):
                total_area += 1
                pt = QPoint(x, y)
                for k in interval_knots:
                    if polygons[k.knot_no].containsPoint(pt, Qt.FillRule.OddEvenFill):
                        knots_area += 1
                        break
                        
        val = knots_area / total_area if total_area > 0 else 0.0
        return min(val, 1.0)

    def _isArrisKnotTopRight(self, knot, board):
        t_z1, t_z2 = self._val(knot.side1_z1), self._val(knot.side1_z2)
        r_y1, r_y2 = self._val(knot.side2_z1), self._val(knot.side2_z2)
        b_z1, b_z2 = self._val(knot.side3_z1), self._val(knot.side3_z2)
        l_y1, l_y2 = self._val(knot.side4_z1), self._val(knot.side4_z2)
        p_z, p_y = self._val(knot.pith_z), self._val(knot.pith_y)

        b_width = board.height

        return (t_z1 >= 0 and t_z2 >= 0) and \
               (r_y1 >= 0 and r_y2 >= 0) and \
               (b_z1 < 0 and b_z2 < 0) and \
               (l_y1 < 0 and l_y2 < 0) and \
               (t_z2 == b_width) and \
               (r_y1 == 0) and \
               (p_z < 0 and p_y < 0)

    def _isArrisKnotTopLeft(self, knot, board):
        t_z1, t_z2 = self._val(knot.side1_z1), self._val(knot.side1_z2)
        r_y1, r_y2 = self._val(knot.side2_z1), self._val(knot.side2_z2)
        b_z1, b_z2 = self._val(knot.side3_z1), self._val(knot.side3_z2)
        l_y1, l_y2 = self._val(knot.side4_z1), self._val(knot.side4_z2)
        p_z, p_y = self._val(knot.pith_z), self._val(knot.pith_y)

        return (t_z1 >= 0 and t_z2 >= 0) and \
               (r_y1 < 0 and r_y2 < 0) and \
               (b_z1 < 0 and b_z2 < 0) and \
               (l_y1 >= 0 and l_y2 >= 0) and \
               (t_z1 == 0) and \
               (l_y1 == 0) and \
               (p_z < 0 and p_y < 0)

    def _isSplayKnotUpperRight(self, knot, board):
        if self._isArrisKnotTopRight(knot, board):
            r_y1, r_y2 = self._val(knot.side2_z1), self._val(knot.side2_z2)
            deb_alt = (r_y2 - r_y1) / board.base
            if deb_alt <= 0.5:
                return deb_alt
        return -1.0

    def _isSplayKnotUpperRightBetter(self, knot, board):
        val_sk = self._isSplayKnotUpperRight(knot, board)
        if val_sk >= 0:
            t_z1, t_z2 = self._val(knot.side1_z1), self._val(knot.side1_z2)
            r_y1, r_y2 = self._val(knot.side2_z1), self._val(knot.side2_z2)
            deb = ((t_z2 - t_z1) + (r_y2 - r_y1)) / (2 * board.height)
            if val_sk < deb:
                return True
        return False

    def _isSplayKnotUpperLeft(self, knot, board):
        if self._isArrisKnotTopLeft(knot, board):
            l_y1, l_y2 = self._val(knot.side4_z1), self._val(knot.side4_z2)
            deb_alt = (l_y2 - l_y1) / board.base
            if deb_alt <= 0.5:
                return deb_alt
        return -1.0

    def _isSplayKnotUpperLeftBetter(self, knot, board):
        val_sk = self._isSplayKnotUpperLeft(knot, board)
        if val_sk >= 0:
            t_z1, t_z2 = self._val(knot.side1_z1), self._val(knot.side1_z2)
            l_y1, l_y2 = self._val(knot.side4_z1), self._val(knot.side4_z2)
            deb = ((t_z2 - t_z1) + (l_y2 - l_y1)) / (2 * board.height)
            if val_sk < deb:
                return True
        return False

    def _SplayKnot(self, current_knot, board):
        if self._isArrisKnotTopRight(current_knot, board):
            if self._isSplayKnotUpperRightBetter(current_knot, board):
                return True
        elif self._isArrisKnotTopLeft(current_knot, board):
            if self._isSplayKnotUpperLeftBetter(current_knot, board):
                return True
        return False

    def _DEB(self, current_knot, board):
        deb = 0.0
        
        if self._isArrisKnotTopRight(current_knot, board):
            t_z1, t_z2 = self._val(current_knot.side1_z1), self._val(current_knot.side1_z2)
            r_y1, r_y2 = self._val(current_knot.side2_z1), self._val(current_knot.side2_z2)
            deb = ((t_z2 - t_z1) + (r_y2 - r_y1)) / (2 * board.height)
            
            val_sk = self._isSplayKnotUpperRight(current_knot, board)
            if val_sk < 0:
                return deb
            else:
                if not self._isSplayKnotUpperRightBetter(current_knot, board):
                    return deb
                else:
                    return val_sk
                    
        elif self._isArrisKnotTopLeft(current_knot, board):
            t_z1, t_z2 = self._val(current_knot.side1_z1), self._val(current_knot.side1_z2)
            l_y1, l_y2 = self._val(current_knot.side4_z1), self._val(current_knot.side4_z2)
            deb = ((t_z2 - t_z1) + (l_y2 - l_y1)) / (2 * board.height)
            
            val_sk = self._isSplayKnotUpperLeft(current_knot, board)
            if val_sk < 0:
                return deb
            else:
                if not self._isSplayKnotUpperLeftBetter(current_knot, board):
                    return deb
                else:
                    return val_sk
                    
        else:
            t_z1, t_z2 = self._val(current_knot.side1_z1), self._val(current_knot.side1_z2)
            if t_z1 >= 0 and t_z2 >= 0:
                deb += (t_z2 - t_z1)
                
            r_y1, r_y2 = self._val(current_knot.side2_z1), self._val(current_knot.side2_z2)
            if r_y1 >= 0 and r_y2 >= 0:
                deb += (r_y2 - r_y1)
                
            b_z1, b_z2 = self._val(current_knot.side3_z1), self._val(current_knot.side3_z2)
            if b_z1 >= 0 and b_z2 >= 0:
                deb += (b_z2 - b_z1)
                
            l_y1, l_y2 = self._val(current_knot.side4_z1), self._val(current_knot.side4_z2)
            if l_y1 >= 0 and l_y2 >= 0:
                deb += (l_y2 - l_y1)
                
            return deb / (2 * board.height)

    def _DAB(self, current_knot, board, interval_knots):
        dab_top = 0
        dab_right = 0
        dab_bottom = 0
        dab_left = 0
        
        b_width = board.height
        b_thick = board.base

        # Top
        for x in range(b_width):
            for k in interval_knots:
                if not self._isSplayKnotUpperRightBetter(k, board) and not self._isSplayKnotUpperLeftBetter(k, board):
                    t_z1, t_z2 = self._val(k.side1_z1), self._val(k.side1_z2)
                    if t_z1 >= 0 and t_z2 >= 0 and t_z1 <= x < t_z2:
                        dab_top += 1
                        break
                        
        # Right
        for x in range(b_thick):
            for k in interval_knots:
                r_y1, r_y2 = self._val(k.side2_z1), self._val(k.side2_z2)
                if r_y1 >= 0 and r_y2 >= 0 and r_y1 <= x < r_y2:
                    dab_right += 1
                    break
                    
        # Bottom
        for x in range(b_width):
            for k in interval_knots:
                b_z1, b_z2 = self._val(k.side3_z1), self._val(k.side3_z2)
                if b_z1 >= 0 and b_z2 >= 0 and b_z1 <= x < b_z2:
                    dab_bottom += 1
                    break
                    
        # Left
        for x in range(b_thick):
            for k in interval_knots:
                l_y1, l_y2 = self._val(k.side4_z1), self._val(k.side4_z2)
                if l_y1 >= 0 and l_y2 >= 0 and l_y1 <= x < l_y2:
                    dab_left += 1
                    break

        dab = (dab_top + dab_right + dab_bottom + dab_left) / (2 * b_width)
        return dab

    def _DEK(self, current_knot, board):
        dek = 0.0
        b_width = board.height
        b_thick = board.base
        
        t_dmin = self._val(current_knot.side1_dmin)
        if t_dmin >= 0:
            t_z1, t_z2 = self._val(current_knot.side1_z1), self._val(current_knot.side1_z2)
            if (t_z2 - t_z1) < t_dmin:
                dek_top = (t_z2 - t_z1) / b_width
            else:
                dek_top = t_dmin / b_width
            dek = max(dek, dek_top)
            
        r_dmin = self._val(current_knot.side2_dmin)
        if r_dmin >= 0:
            r_y1, r_y2 = self._val(current_knot.side2_z1), self._val(current_knot.side2_z2)
            if (r_y2 - r_y1) < r_dmin:
                dek_right = (r_y2 - r_y1) / b_thick
            else:
                dek_right = r_dmin / b_thick
            dek = max(dek, dek_right)
            
        b_dmin = self._val(current_knot.side3_dmin)
        if b_dmin >= 0:
            b_z1, b_z2 = self._val(current_knot.side3_z1), self._val(current_knot.side3_z2)
            if (b_z2 - b_z1) < b_dmin:
                dek_bottom = (b_z2 - b_z1) / b_width
            else:
                dek_bottom = b_dmin / b_width
            dek = max(dek, dek_bottom)
            
        l_dmin = self._val(current_knot.side4_dmin)
        if l_dmin >= 0:
            l_y1, l_y2 = self._val(current_knot.side4_z1), self._val(current_knot.side4_z2)
            if (l_y2 - l_y1) < l_dmin:
                dek_left = (l_y2 - l_y1) / b_thick
            else:
                dek_left = l_dmin / b_thick
            dek = max(dek, dek_left)
            
        return dek

    def _isFaceKnot(self, knot):
        r_y1, r_y2 = self._val(knot.side2_z1), self._val(knot.side2_z2)
        l_y1, l_y2 = self._val(knot.side4_z1), self._val(knot.side4_z2)
        return (r_y1 >= 0 and r_y2 >= 0) or (l_y1 >= 0 and l_y2 >= 0)

    def _EEB(self, current_knot, board):
        b_width = board.height
        eeb = 0.0
        
        t_z1_tmp = b_width
        b_z1_tmp = b_width
        
        t_z1, t_z2 = self._val(current_knot.side1_z1), self._val(current_knot.side1_z2)
        r_y1, r_y2 = self._val(current_knot.side2_z1), self._val(current_knot.side2_z2)
        b_z1, b_z2 = self._val(current_knot.side3_z1), self._val(current_knot.side3_z2)
        l_y1, l_y2 = self._val(current_knot.side4_z1), self._val(current_knot.side4_z2)
        p_z, p_y = self._val(current_knot.pith_z), self._val(current_knot.pith_y)

        if self._isFaceKnot(current_knot):
            has_r = r_y1 >= 0 and r_y2 >= 0
            has_l = l_y1 >= 0 and l_y2 >= 0
            has_p = p_z >= 0 and p_y >= 0
            
            if has_r and has_l:
                eeb = b_width
            elif has_l and not has_r and not has_p:
                eeb = max(t_z2, b_z2)
            elif not has_l and has_r and not has_p:
                if t_z1 >= 0 and t_z2 >= 0: t_z1_tmp = t_z1
                if b_z1 >= 0 and b_z2 >= 0: b_z1_tmp = b_z1
                eeb = -1 * max(b_width - t_z1_tmp, b_width - b_z1_tmp)
            elif has_l and not has_r and has_p:
                eeb = max(max(t_z2, b_z2), p_z)
            elif not has_l and has_r and has_p:
                if t_z1 >= 0 and t_z2 >= 0: t_z1_tmp = t_z2
                if b_z1 >= 0 and b_z2 >= 0: b_z1_tmp = b_z2
                eeb = -1 * max(max(b_width - t_z1_tmp, b_width - b_z1_tmp), b_width - p_z)
                
        return eeb / b_width if b_width > 0 else 0.0

    def _EAB(self, board, interval_knots):
        eeb_left_max = 0.0
        eeb_right_min = 0.0
        
        for k in interval_knots:
            eeb_val = self._EEB(k, board)
            if eeb_val < 0:
                if eeb_val < eeb_right_min:
                    eeb_right_min = eeb_val
            elif eeb_val > 0:
                if eeb_val > eeb_left_max:
                    eeb_left_max = eeb_val
                    
        val = eeb_left_max + abs(eeb_right_min)
        return 1.0 if val >= 1.0 else val
